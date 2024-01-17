from django.conf import settings
import django
from pathlib import Path
from django.db import connections


def setup_django(data_dir: Path, **kwargs):
    settings.configure(
        INSTALLED_APPS=["apps.authz", "apps.order", "apps.group"],
        DATABASES={
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
            },
        },
        **kwargs,
    )
    django.setup()


def get_tables(db):
    connection = connections[db]
    cursor = connection.cursor()

    cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='table' and name !='sqlite_sequence'"
    )
    tables = {item[0] for item in cursor.fetchall()}

    return tables


def drop_tables(db):
    connection = connections[db]
    cursor = connection.cursor()
    tables = get_tables(db)

    for table_name in tables:
        cursor.execute(f"DROP TABLE {table_name}")

    connection.commit()
