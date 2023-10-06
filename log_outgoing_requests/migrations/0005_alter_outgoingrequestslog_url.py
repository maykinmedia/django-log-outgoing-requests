# Generated by Django 4.1 on 2023-10-06 12:08

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("log_outgoing_requests", "0004_alter_outgoingrequestslog_hostname_and_more"),
    ]

    operations = [
        migrations.AlterField(
            model_name="outgoingrequestslog",
            name="url",
            field=models.TextField(
                help_text="The url of the outgoing request.",
                verbose_name="URL",
            ),
        ),
    ]
