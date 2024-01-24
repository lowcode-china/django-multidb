from django.db import models
from typing_extensions import Self
from django_multidb.models.deletion import Collector
from django_multidb.models.fields.rel import RelField, RelManyField
from django.db.models import Q

__all__ = ["QuerySet"]


class QuerySet(models.QuerySet):
    def filter(self, *args, **kwargs) -> Self:
        predicates = []

        for key, value in kwargs.items():
            parts = key.split("__", maxsplit=1)
            related_field = getattr(getattr(self.model, parts[0]), "field", None)
            if (
                related_field
                and isinstance(related_field, (RelField, RelManyField))
                and len(parts) > 1
            ):
                related_model = related_field.remote_field.model
                sub_qs = related_model.objects.values("id").filter(
                    **{f"{parts[1]}": value}
                )
                ids = [item["id"] for item in sub_qs]

                predicates.append(Q(**{f"{parts[0]}_id__in": ids}))
            else:
                predicates.append(Q(**{f"{key}": value}))

        return super().filter(*predicates)

    def delete(self):
        """Delete the records in the current QuerySet."""
        self._not_support_combined_queries("delete")
        if self.query.is_sliced:
            raise TypeError("Cannot use 'limit' or 'offset' with delete().")
        if self.query.distinct or self.query.distinct_fields:
            raise TypeError("Cannot call delete() after .distinct().")
        if self._fields is not None:
            raise TypeError("Cannot call delete() after .values() or .values_list()")

        del_query = self._chain()

        # The delete is actually 2 queries - one to find related objects,
        # and one to delete. Make sure that the discovery of related
        # objects is performed on the same database as the deletion.
        del_query._for_write = True

        # Disable non-supported fields.
        del_query.query.select_for_update = False
        del_query.query.select_related = False
        del_query.query.clear_ordering(force=True)

        collector = Collector(using=del_query.db, origin=self)
        collector.collect(del_query)
        deleted, _rows_count = collector.delete()

        # Clear the result cache, in case this QuerySet gets reused.
        self._result_cache = None
        return deleted, _rows_count
