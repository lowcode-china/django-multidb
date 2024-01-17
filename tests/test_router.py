from utils import setup_django, get_tables, drop_tables
from django.core.management import call_command
from pathlib import Path
import pytest


@pytest.mark.forked
def test_model_routing(tmp_path: Path):
    setup_django(
        data_dir=tmp_path,
        DATABASE_ROUTERS=["django_multidb.routers.DatabaseModelsRouter"],
        DATABASE_MODELS_MAPPING={"permission": "db1", "role": "db2"},
    )
    call_command("makemigrations", "authz", interactive=False, verbosity=0)
    call_command("migrate", "authz", database="db1", interactive=False, verbosity=0)
    call_command("migrate", "authz", database="db2", interactive=False, verbosity=0)

    assert get_tables("db1") == {"django_migrations", "authz_permission"}
    assert get_tables("db2") == {
        "authz_role_permissions",
        "django_migrations",
        "authz_role",
    }


@pytest.mark.forked
def test_app_routing(tmp_path: Path):
    setup_django(
        data_dir=tmp_path,
        DATABASE_ROUTERS=["django_multidb.routers.DatabaseAppsRouter"],
        DATABASE_APPS_MAPPING={"authz": "db1", "order": "db2"},
    )

    call_command("makemigrations", "authz", interactive=False, verbosity=0)
    call_command("makemigrations", "order", interactive=False, verbosity=0)
    call_command("migrate", "authz", database="db1", interactive=False, verbosity=0)
    call_command("migrate", "order", database="db2", interactive=False, verbosity=0)

    assert get_tables("db1") == {
        "authz_user",
        "authz_permission",
        "django_migrations",
        "authz_role_permissions",
        "authz_user_roles",
        "authz_role",
    }
    assert get_tables("db2") == {"order_order", "django_migrations"}

    drop_tables("db1")
    drop_tables("db2")

    call_command("migrate", "authz", database="db2", interactive=False, verbosity=0)
    call_command("migrate", "order", database="db1", interactive=False, verbosity=0)

    assert get_tables("db1") == {"django_migrations"}
    assert get_tables("db2") == {"django_migrations"}

"""debug cases
python -m pytest tests/test_router.py
"""