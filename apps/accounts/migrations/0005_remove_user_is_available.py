from django.db import migrations


class Migration(migrations.Migration):
    """
    Drops the manual available/busy toggle. Availability is now derived
    from assigned tickets (apps.tickets.services.active_tickets_count), so
    the stored flag had nothing left to mean.

    Reversible: migrating back re-adds the column with its old default
    (True) for every user — the previous manual values are not restored,
    which is fine, since they no longer described anything real.
    """

    dependencies = [
        ("accounts", "0004_user_is_supervisor"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="user",
            name="is_available",
        ),
    ]
