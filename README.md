# django-multidb

## Configure different apps or models to different database instances.

Django settings
```python
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": data_dir / "default.sqlite3",
    },
    "db1": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": data_dir / "db1.sqlite3",
    },
    "db2": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": data_dir / "db2.sqlite3",
    },
    "db3": {
        "ENGINE": "djongo",
        "NAME": "db3",
    }
}
```

Configure different models to different database instances.

```python
DATABASE_ROUTERS = ["django_multidb.routers.DatabaseModelsRouter"] 
DATABASE_MODELS_MAPPING = {"permission": "db1", "role": "db2"}
```

The Permission model uses db1, and the Role model uses db2. Run the migrate command to create tables.

```shell
python manage.py migrate --database=db1 # create permission
python manage.py migrate --database=db2 # create role
```

Configure different apps to different database instances.

```python
DATABASE_ROUTERS = ["django_multidb.routers.DatabaseAppsRouter"]
DATABASE_APPS_MAPPING = {"authz": "db1", "order": "db2"}
```

The app authz uses db1 instance, and the order uses db2 instance. Run the migrate command to create tables.
c
```shell
python manage.py migrate --database=db1 # create all tables for the authz app. 
python manage.py migrate --database=db2 # Create all tables for the order app.
```

Tested association queries and deletions between different SQLite instances and MongoDB. More use cases can be referred to in the tests.

# About the Queryset.filter method

Due to the involvement of cross-database instance querying, even direct associations across different database architectures, the filter method has been overridden.

First, query the IDs of data in the associated table and then perform a query on the main table using an IN condition with these IDs, rather than using JOIN syntax for the query.
