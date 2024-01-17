from django.db import models
from djongo import models as djongo_models
from apps.authz.models import User
from django_multidb.models.query import QuerySet
from django_multidb.models.fields.rel import RelField, RelManyField


class Group(djongo_models.Model):
    objects = QuerySet.as_manager()

    _id = djongo_models.ObjectIdField()
    name = djongo_models.CharField(max_length=50)
    admin = RelField(to=User, on_delete=models.CASCADE, null=True)
    users = RelManyField(to=User, null=True)
