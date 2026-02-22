# Generated manually

from django.db import migrations, models

class Migration(migrations.Migration):

    dependencies = [
        ("users", "0023_distributorprofile_broker_code"),
    ]

    operations = [
        migrations.AlterField(
            model_name="distributorprofile",
            name="arn_number",
            field=models.CharField(blank=True, max_length=50, null=True, unique=True, help_text="AMFI Registration Number"),
        ),
        migrations.AlterField(
            model_name="distributorprofile",
            name="broker_code",
            field=models.CharField(help_text="Sub Broker Code (e.g. BBF0001)", max_length=20, unique=True),
        ),
    ]
