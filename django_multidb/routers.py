from django.conf import settings


class DatabaseAppsRouter:
    @property
    def mapping(self):
        return getattr(settings, "DATABASE_APPS_MAPPING", {})

    def db_for_read(self, model, **hints):
        return self.mapping.get(model._meta.app_label, "default")

    def db_for_write(self, model, **hints):
        return self.mapping.get(model._meta.app_label, "default")

    def allow_relation(self, obj_1, obj_2, **hints):
        return self.mapping.get(obj_1._meta.app_label) and self.mapping.get(
            obj_2._meta.app_label, "default"
        )

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        return self.mapping.get(app_label, "default") == db


class DatabaseModelsRouter(object):
    @property
    def mapping(self):
        return getattr(settings, "DATABASE_MODELS_MAPPING", {})

    def db_for_read(self, model, **hints):
        return self.mapping.get(model._meta.model_name, "default")

    def db_for_write(self, model, **hints):
        return self.mapping.get(model._meta.model_name, "default")

    def allow_relation(self, obj_1, obj_2, **hints):
        return self.mapping.get(obj_1._meta.model_name, "default") and self.mapping.get(
            obj_2._meta.model_name, "default"
        )

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        return self.mapping.get(model_name, "default") == db
