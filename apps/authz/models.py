from django.db import models
from django_multidb.models.base import BaseModel
from django_multidb.models.fields.rel import RelField, RelManyField


class Permission(BaseModel):
    name = models.CharField(max_length=50)


class Role(BaseModel):
    name = models.CharField(max_length=50)
    parent = models.ForeignKey(
        to="Role", on_delete=models.CASCADE, null=True, related_name="children"
    )
    permissions = models.ManyToManyField(to=Permission, db_constraint=False)


class User(BaseModel):
    name = models.CharField(max_length=50)
    current_role = RelField(
        to=Role, null=True, on_delete=models.SET_NULL, related_name="users"
    )
    roles = RelManyField(to=Role, null=True)
