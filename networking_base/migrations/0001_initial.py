# Generated by Django 3.2.3 on 2021-05-16 19:20

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Contact",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("name", models.CharField(max_length=50)),
                ("frequency_in_days", models.IntegerField()),
                ("description", models.TextField(blank=True, null=True)),
                (
                    "linkedin_url",
                    models.URLField(blank=True, max_length=100, null=True),
                ),
                ("twitter_url", models.URLField(blank=True, max_length=100, null=True)),
                (
                    "phone_number",
                    models.CharField(blank=True, max_length=50, null=True),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="Interaction",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("title", models.CharField(max_length=100)),
                ("description", models.TextField()),
                ("was_at", models.DateTimeField()),
                (
                    "contact",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="interactions",
                        to="networking_base.contact",
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="InteractionType",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("slug", models.SlugField()),
                ("name", models.CharField(max_length=50)),
                ("description", models.CharField(max_length=250)),
            ],
        ),
        migrations.CreateModel(
            name="Reminder",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("due_on", models.DateField()),
                ("skipped_at", models.DateTimeField()),
            ],
        ),
        migrations.CreateModel(
            name="CalendarInteraction",
            fields=[
                (
                    "interaction_ptr",
                    models.OneToOneField(
                        auto_created=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        parent_link=True,
                        primary_key=True,
                        serialize=False,
                        to="networking_base.interaction",
                    ),
                ),
                ("google_calendar_id", models.CharField(max_length=100)),
                ("url", models.URLField()),
            ],
            bases=("networking_base.interaction",),
        ),
        migrations.CreateModel(
            name="EmailInteraction",
            fields=[
                (
                    "interaction_ptr",
                    models.OneToOneField(
                        auto_created=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        parent_link=True,
                        primary_key=True,
                        serialize=False,
                        to="networking_base.interaction",
                    ),
                ),
                ("gmail_message_id", models.CharField(max_length=100)),
            ],
            bases=("networking_base.interaction",),
        ),
        migrations.AddField(
            model_name="interaction",
            name="type",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                to="networking_base.interactiontype",
            ),
        ),
        migrations.CreateModel(
            name="EmailAddress",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("email", models.EmailField(max_length=100)),
                (
                    "contact",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="emails",
                        to="networking_base.contact",
                    ),
                ),
            ],
            options={
                "unique_together": {("contact", "email")},
            },
        ),
    ]
