# Generated by Django 4.2.1 on 2023-05-09 07:48

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("log_outgoing_requests", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="OutgoingRequestsLogConfig",
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
                (
                    "save_to_db",
                    models.IntegerField(
                        blank=True,
                        choices=[(None, "Use default"), (0, "No"), (1, "Yes")],
                        help_text="Whether request logs should be saved to the database (default: True)",
                        null=True,
                        verbose_name="Save logs to database",
                    ),
                ),
                (
                    "save_body",
                    models.IntegerField(
                        blank=True,
                        choices=[(None, "Use default"), (0, "No"), (1, "Yes")],
                        help_text="Wheter the body of the request and response should be logged (default: False). This option is ignored if 'Save Logs to database' is set to False.",
                        null=True,
                        verbose_name="Save request + response body",
                    ),
                ),
            ],
            options={
                "verbose_name": "Outgoing Requests Logs Configuration",
            },
        ),
        migrations.AlterModelOptions(
            name="outgoingrequestslog",
            options={
                "permissions": [("can_view_logs", "Can view outgoing request logs")],
                "verbose_name": "Outgoing Requests Log",
                "verbose_name_plural": "Outgoing Requests Logs",
            },
        ),
        migrations.AddField(
            model_name="outgoingrequestslog",
            name="req_body",
            field=models.TextField(
                blank=True,
                help_text="The request body.",
                null=True,
                verbose_name="Request body",
            ),
        ),
        migrations.AddField(
            model_name="outgoingrequestslog",
            name="res_body",
            field=models.JSONField(
                blank=True,
                help_text="The response body.",
                null=True,
                verbose_name="Response body",
            ),
        ),
    ]