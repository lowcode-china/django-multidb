from typing import Any
from django.db import models


class RelField(models.ForeignKey):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        kwargs["db_constraint"] = False
        super().__init__(*args, **kwargs)


class RelManyField(models.ManyToManyField):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        kwargs["db_constraint"] = False
        super().__init__(*args, **kwargs)

