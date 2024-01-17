# Generated by Django 4.1.13 on 2024-01-17 12:50

from django.db import migrations
import django.db.models.manager


class Migration(migrations.Migration):
    dependencies = [
        ("authz", "0004_alter_role_permissions"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="permission",
            options={"base_manager_name": "base_manager"},
        ),
        migrations.AlterModelOptions(
            name="role",
            options={"base_manager_name": "base_manager"},
        ),
        migrations.AlterModelOptions(
            name="user",
            options={"base_manager_name": "base_manager"},
        ),
        migrations.AlterModelManagers(
            name="permission",
            managers=[
                ("objects", django.db.models.manager.Manager()),
                ("base_manager", django.db.models.manager.Manager()),
            ],
        ),
        migrations.AlterModelManagers(
            name="role",
            managers=[
                ("objects", django.db.models.manager.Manager()),
                ("base_manager", django.db.models.manager.Manager()),
            ],
        ),
        migrations.AlterModelManagers(
            name="user",
            managers=[
                ("objects", django.db.models.manager.Manager()),
                ("base_manager", django.db.models.manager.Manager()),
            ],
        ),
    ]
