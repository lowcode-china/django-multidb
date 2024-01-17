# pyright: reportGeneralTypeIssues=false,reportOptionalMemberAccess=false

from typing import Any
from django.db import models
from django.db import router
from django_multidb.models.query import QuerySet
from django_multidb.models.deletion import Collector
from django.db.models.options import Options


class BaseModel(models.Model):
    objects = QuerySet.as_manager()

    def delete(self, using=None, keep_parents=False):
        if self.pk is None:
            raise ValueError(
                "%s object can't be deleted because its %s attribute is set "
                "to None." % (self._meta.object_name, self._meta.pk.attname)
            )
        using = using or router.db_for_write(self.__class__, instance=self)
        collector = Collector(using=using, origin=self)
        collector.collect([self], keep_parents=keep_parents)
        return collector.delete()

    class Meta:
        abstract = True
