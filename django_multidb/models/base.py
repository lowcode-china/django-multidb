from django.db import models
from django.db import router
from django_multidb.models.query import QuerySet
from django_multidb.models.deletion import Collector


class BaseModel(models.Model):
    objects = QuerySet.as_manager()

    def delete(self, using=None, keep_parents=False):
        if self.pk is None:
            raise ValueError(
                "%s object can't be deleted because its %s attribute is set "
                "to None." % (self._meta.object_name, self._meta.pk.attname)  # type: ignore
            )
        using = using or router.db_for_write(self.__class__, instance=self)

        # ! Custom Collector, instead of using self.using, obtain the actual database of the related model through router.db_for_write.
        collector = Collector(using=using, origin=self)  # type: ignore
        collector.collect([self], keep_parents=keep_parents)
        return collector.delete()

    class Meta:
        abstract = True
