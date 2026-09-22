from django.db import migrations
from django.db.models import Min


def backfill(apps, schema_editor):
    """
    Existing tickets get their first-response time from the audit trail: the
    earliest STATUS_CHANGED -> IN_PROGRESS entry. Tickets that never got
    there keep NULL (no response yet, or cancelled while still OPEN).
    """
    Ticket = apps.get_model("tickets", "Ticket")
    TicketHistory = apps.get_model("tickets", "TicketHistory")

    first_starts = (
        TicketHistory.objects.filter(action="STATUS_CHANGED", new_value="IN_PROGRESS")
        .values("ticket_id")
        .annotate(first=Min("created_at"))
    )
    for row in first_starts:
        Ticket.objects.filter(pk=row["ticket_id"], first_response_at__isnull=True).update(
            first_response_at=row["first"]
        )


class Migration(migrations.Migration):
    dependencies = [
        ("tickets", "0010_category_response_sla_minutes_and_more"),
    ]

    operations = [
        migrations.RunPython(backfill, migrations.RunPython.noop),
    ]
