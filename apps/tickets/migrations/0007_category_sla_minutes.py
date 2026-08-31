from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tickets', '0006_ticketnote'),
    ]

    operations = [
        migrations.AddField(
            model_name='category',
            name='sla_minutes',
            field=models.PositiveIntegerField(
                default=60,
                help_text=(
                    "Expected response time for a ticket in this category, "
                    "in minutes (e.g. towels: 15, power outage: 10). Drives "
                    "both the guest-facing \"estimated response time\" and "
                    "the operator overdue highlight — there is deliberately "
                    "only one number to configure, not a separate one for "
                    "each."
                ),
            ),
        ),
    ]
