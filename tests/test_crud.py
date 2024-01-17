from utils import setup_django, connections
from django.core.management import call_command
from pathlib import Path
import pytest


@pytest.mark.forked
def test_create_or_update(tmp_path):
    setup_django(
        data_dir=tmp_path,
        DATABASE_ROUTERS=["django_multidb.routers.DatabaseModelsRouter"],
        DATABASE_MODELS_MAPPING={
            "role": "db1",
            "user": "db2",
        },
    )

    call_command("makemigrations", "authz", interactive=False, verbosity=0)
    call_command("migrate", "authz", database="db1", interactive=False, verbosity=0)
    call_command("migrate", "authz", database="db2", interactive=False, verbosity=0)

    from apps.authz.models import Role, User

    role = Role(name="root")
    role.save()

    User(name="tom", current_role=role).save()

    User.objects.update_or_create(name="tom", defaults={"current_role": role})

    connection = connections["db2"]
    cursor = connection.cursor()
    cursor.execute("SELECT * FROM authz_user WHERE name='tom'")
    user = cursor.fetchone()
    assert user and user[2] == getattr(role, "id")


@pytest.mark.forked
def test_batch_create_or_update(tmp_path):
    setup_django(
        data_dir=tmp_path,
        DATABASE_ROUTERS=["django_multidb.routers.DatabaseModelsRouter"],
        DATABASE_MODELS_MAPPING={
            "role": "db1",
            "user": "db2",
        },
    )

    call_command("makemigrations", "authz", interactive=False, verbosity=0)
    call_command("migrate", "authz", database="db1", interactive=False, verbosity=0)
    call_command("migrate", "authz", database="db2", interactive=False, verbosity=0)

    from apps.authz.models import Role, User

    role = Role(name="root")
    role.save()

    User.objects.bulk_create(
        [
            User(name="tom", current_role=role),
            User(name="jack", current_role=role),
        ]
    )

    connection = connections["db2"]
    cursor = connection.cursor()
    cursor.execute("SELECT * FROM authz_user")
    users = cursor.fetchall()

    assert users[0][2] == users[1][2] == getattr(role, "id")

    role = Role(name="admin")
    role.save()

    users = User.objects.filter()
    for user in users:
        user.current_role = role

    User.objects.bulk_update(users, fields=["current_role"])

    connection = connections["db2"]
    cursor = connection.cursor()
    cursor.execute("SELECT * FROM authz_user")
    users = cursor.fetchall()
    assert users[0][2] == users[1][2] == getattr(role, "id")


@pytest.mark.forked
def test_delete(tmp_path):
    setup_django(
        data_dir=tmp_path,
        DATABASE_ROUTERS=["django_multidb.routers.DatabaseModelsRouter"],
        DATABASE_MODELS_MAPPING={
            "role_permissions": "db1",
            "role": "db1",
            "user": "db2",
            "user_roles": "db2",
            "group": "db3",
            "group_users": "db3",
        },
    )

    call_command("makemigrations", "authz", interactive=False, verbosity=0)
    call_command("migrate", "authz", database="db1", interactive=False, verbosity=0)
    call_command("migrate", "authz", database="db2", interactive=False, verbosity=0)

    from apps.authz.models import Role, User
    from apps.group.models import Group

    role = Role(name="root")
    role.save()
    roles = Role.objects.filter()

    user = User(name="tom", current_role=role)
    user.save()
    user.roles.set(roles, clear=True)
    user.save()
    role.delete()

    user = User.objects.get(name="tom")
    users = User.objects.filter()
    assert user.current_role is None

    group = Group(name="group", admin=user)
    group.save()
    group.users.set(users, clear=True)
    group.save()

    user.delete()
    assert not Group.objects.filter(_id=group._id).exists()

    user = User(name="tom")
    user.save()
    group, _ = Group.objects.get_or_create(name="group", admin=user)

    User.objects.filter(name="tom").delete()
    assert not Group.objects.filter(_id=group._id).exists()


@pytest.mark.forked
def test_filter(tmp_path):
    setup_django(
        data_dir=tmp_path,
        DATABASE_ROUTERS=["django_multidb.routers.DatabaseModelsRouter"],
        DATABASE_MODELS_MAPPING={
            "permission": "default",
            "role_permissions": "db1",
            "role": "db1",
            "user": "db2",
            "user_roles": "db2",
            "group": "db3",
            "group_users": "db3",
        },
    )

    call_command("makemigrations", "authz", interactive=False, verbosity=0)
    call_command("migrate", "authz", database="db1", interactive=False, verbosity=0)
    call_command("migrate", "authz", database="db2", interactive=False, verbosity=0)
    call_command("migrate", "authz", database="default", interactive=False, verbosity=0)

    from apps.authz.models import Role, User, Permission
    from apps.group.models import Group

    permission = Permission(name="root")
    permission.save()
    permissions = Permission.objects.filter()

    role = Role(name="root")
    role.save()
    role.permissions.set(permissions, clear=True)
    role.save()
    roles = Role.objects.filter()

    user = User(name="tom", current_role=role)
    user.save()
    user.roles.set(roles, clear=True)
    user.save()
    users = User.objects.filter()

    group = Group(name="group", admin=user)
    group.save()
    group.users.set(users, clear=True)
    group.save()

    qs = Group.objects.filter(
        admin__current_role__name="root", admin__current_role__id__in=[1]
    )

    assert len(qs)
    qs = Group.objects.filter(
        admin__current_role__name="root", admin__current_role__id__in=[2]
    )
    assert not len(qs)


"""debug cases
python -m pytest tests/test_crud.py
"""
