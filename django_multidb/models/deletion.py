from django.db.models import deletion
from django.db.models.deletion import (
    get_candidate_relations_to_delete,
    DO_NOTHING,
    ProtectedError,
    RestrictedError,
)
from django.db.models import query_utils
from django.db import router
from collections import Counter
from operator import attrgetter
from django.db import transaction
from django.db.models import query_utils, signals, sql
from collections import Counter, defaultdict
from itertools import chain


class Collector(deletion.Collector):
    def collect(
        self,
        objs,
        source=None,
        nullable=False,
        collect_related=True,
        source_attr=None,
        reverse_dependency=False,
        keep_parents=False,
        fail_on_restricted=True,
    ):
        """
        Add 'objs' to the collection of objects to be deleted as well as all
        parent instances.  'objs' must be a homogeneous iterable collection of
        model instances (e.g. a QuerySet).  If 'collect_related' is True,
        related objects will be handled by their respective on_delete handler.

        If the call is the result of a cascade, 'source' should be the model
        that caused it and 'nullable' should be set to True, if the relation
        can be null.

        If 'reverse_dependency' is True, 'source' will be deleted before the
        current model, rather than after. (Needed for cascading to parent
        models, the one case in which the cascade follows the forwards
        direction of an FK rather than the reverse direction.)

        If 'keep_parents' is True, data of parent model's will be not deleted.

        If 'fail_on_restricted' is False, error won't be raised even if it's
        prohibited to delete such objects due to RESTRICT, that defers
        restricted object checking in recursive calls where the top-level call
        may need to collect more objects to determine whether restricted ones
        can be deleted.
        """
        if self.can_fast_delete(objs):
            self.fast_deletes.append(objs)
            return
        new_objs = self.add(
            objs, source, nullable, reverse_dependency=reverse_dependency
        )
        if not new_objs:
            return

        model = new_objs[0].__class__

        if not keep_parents:
            # Recursively collect concrete model's parent models, but not their
            # related objects. These will be found by meta.get_fields()
            concrete_model = model._meta.concrete_model
            for ptr in concrete_model._meta.parents.values():
                if ptr:
                    parent_objs = [getattr(obj, ptr.name) for obj in new_objs]
                    self.collect(
                        parent_objs,
                        source=model,
                        source_attr=ptr.remote_field.related_name,
                        collect_related=False,
                        reverse_dependency=True,
                        fail_on_restricted=False,
                    )
        if not collect_related:
            return

        if keep_parents:
            parents = set(model._meta.get_parent_list())
        model_fast_deletes = defaultdict(list)
        protected_objects = defaultdict(list)
        for related in get_candidate_relations_to_delete(model._meta):
            # Preserve parent reverse relationships if keep_parents=True.
            if keep_parents and related.model in parents:
                continue
            field = related.field
            if field.remote_field.on_delete == DO_NOTHING:
                continue
            related_model = related.related_model
            if self.can_fast_delete(related_model, from_field=field):
                model_fast_deletes[related_model].append(field)
                continue
            batches = self.get_del_batches(new_objs, [field])
            for batch in batches:
                sub_objs = self.related_objects(related_model, [field], batch)
                # Non-referenced fields can be deferred if no signal receivers
                # are connected for the related model as they'll never be
                # exposed to the user. Skip field deferring when some
                # relationships are select_related as interactions between both
                # features are hard to get right. This should only happen in
                # the rare cases where .related_objects is overridden anyway.
                if not (
                    sub_objs.query.select_related
                    or self._has_signal_listeners(related_model)
                ):
                    referenced_fields = set(
                        chain.from_iterable(
                            (rf.attname for rf in rel.field.foreign_related_fields)
                            for rel in get_candidate_relations_to_delete(
                                related_model._meta
                            )
                        )
                    )
                    sub_objs = sub_objs.only(*tuple(referenced_fields))
                if sub_objs:
                    try:
                        field.remote_field.on_delete(self, field, sub_objs, sub_objs.db)
                    except ProtectedError as error:
                        key = "'%s.%s'" % (field.model.__name__, field.name)
                        protected_objects[key] += error.protected_objects
        if protected_objects:
            raise ProtectedError(
                "Cannot delete some instances of model %r because they are "
                "referenced through protected foreign keys: %s."
                % (
                    model.__name__,
                    ", ".join(protected_objects),
                ),
                set(chain.from_iterable(protected_objects.values())),
            )
        for related_model, related_fields in model_fast_deletes.items():
            batches = self.get_del_batches(new_objs, related_fields)
            for batch in batches:
                sub_objs = self.related_objects(related_model, related_fields, batch)
                self.fast_deletes.append(sub_objs)
        for field in model._meta.private_fields:
            if hasattr(field, "bulk_related_objects"):
                # It's something like generic foreign key.
                sub_objs = field.bulk_related_objects(new_objs, self.using)
                self.collect(
                    sub_objs, source=model, nullable=True, fail_on_restricted=False
                )

        if fail_on_restricted:
            # Raise an error if collected restricted objects (RESTRICT) aren't
            # candidates for deletion also collected via CASCADE.
            for related_model, instances in self.data.items():
                self.clear_restricted_objects_from_set(related_model, instances)
            for qs in self.fast_deletes:
                self.clear_restricted_objects_from_queryset(qs.model, qs)
            if self.restricted_objects.values():
                restricted_objects = defaultdict(list)
                for related_model, fields in self.restricted_objects.items():
                    for field, objs in fields.items():
                        if objs:
                            key = "'%s.%s'" % (related_model.__name__, field.name)
                            restricted_objects[key] += objs
                if restricted_objects:
                    raise RestrictedError(
                        "Cannot delete some instances of model %r because "
                        "they are referenced through restricted foreign keys: "
                        "%s."
                        % (
                            model.__name__,
                            ", ".join(restricted_objects),
                        ),
                        set(chain.from_iterable(restricted_objects.values())),
                    )

    def related_objects(self, related_model, related_fields, objs):
        """
        Get a QuerySet of the related model to objs via related fields.
        """
        predicate = query_utils.Q(
            *((f"{related_field.name}__in", objs) for related_field in related_fields),
            _connector=query_utils.Q.OR,
        )
        using = router.db_for_write(related_model)
        return related_model._base_manager.using(using).filter(predicate)

    def delete(self):
        # sort instance collections
        for model, instances in self.data.items():
            self.data[model] = sorted(instances, key=attrgetter("pk"))

        # if possible, bring the models in an order suitable for databases that
        # don't support transactions or cannot defer constraint checks until the
        # end of a transaction.
        self.sort()
        # number of objects deleted for each model label
        deleted_counter = Counter()

        # Optimize for the case with a single obj and no dependencies
        if len(self.data) == 1 and len(instances) == 1:
            instance = list(instances)[0]
            if self.can_fast_delete(instance):
                with transaction.mark_for_rollback_on_error(router.db_for_write(model)):
                    count = sql.DeleteQuery(model).delete_batch(
                        [instance.pk], router.db_for_write(model)
                    )
                setattr(instance, model._meta.pk.attname, None)
                return count, {model._meta.label: count}

        with transaction.atomic(using=self.using, savepoint=False):
            # send pre_delete signals
            for model, obj in self.instances_with_model():
                if not model._meta.auto_created:
                    signals.pre_delete.send(
                        sender=model,
                        instance=obj,
                        using=router.db_for_write(model),
                        origin=self.origin,
                    )

            # fast deletes
            for qs in self.fast_deletes:
                count = qs._raw_delete(using=qs.db)
                if count:
                    deleted_counter[qs.model._meta.label] += count

            # update fields
            for model, instances_for_fieldvalues in self.field_updates.items():
                for (field, value), instances in instances_for_fieldvalues.items():
                    query = sql.UpdateQuery(model)
                    query.update_batch(
                        [obj.pk for obj in instances],
                        {field.name: value},
                        router.db_for_write(model),
                    )

            # reverse instance collections
            for instances in self.data.values():
                instances.reverse()

            # delete instances
            for model, instances in self.data.items():
                query = sql.DeleteQuery(model)
                pk_list = [obj.pk for obj in instances]
                count = query.delete_batch(pk_list, router.db_for_write(model))
                if count:
                    deleted_counter[model._meta.label] += count

                if not model._meta.auto_created:
                    for obj in instances:
                        signals.post_delete.send(
                            sender=model,
                            instance=obj,
                            using=router.db_for_write(model),
                            origin=self.origin,
                        )

        # update collected instances
        for instances_for_fieldvalues in self.field_updates.values():
            for (field, value), instances in instances_for_fieldvalues.items():
                for obj in instances:
                    setattr(obj, field.attname, value)
        for model, instances in self.data.items():
            for instance in instances:
                setattr(instance, model._meta.pk.attname, None)
        return sum(deleted_counter.values()), dict(deleted_counter)
