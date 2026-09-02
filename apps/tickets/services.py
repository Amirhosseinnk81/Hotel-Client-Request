"""
Cross-department aggregate stats for hotel admins (Stage 2.4).

Deliberately kept as a plain function (not tied to DRF or Django Admin)
so both the API endpoint (AdminStatsSummaryView) and the Django Admin
stats page share exactly one implementation instead of two copies of
the same aggregation logic drifting apart.
"""

from datetime import timedelta

from django.db.models import Avg, Count, DurationField, ExpressionWrapper, F, Q
from django.utils import timezone

from apps.departments.models import Department

from .models import Ticket

# How far back "average resolution time" looks. A fixed 30-day window
# rather than "all time" so the number reflects current operational
# performance, not diluted by however long the hotel has used the system.
RESOLUTION_WINDOW = timedelta(days=30)


def compute_admin_stats_summary():
    by_status = {
        row["status"]: row["count"]
        for row in Ticket.objects.values("status").annotate(count=Count("id"))
    }
    # Every status key is always present (0 rather than missing) so the
    # frontend/template never has to guess-and-default.
    by_status = {
        value: by_status.get(value, 0) for value, _label in Ticket.Status.choices
    }

    # Built from Department (not Ticket, grouped by department) so a
    # department with zero tickets still shows a 0 row instead of
    # silently disappearing from the report.
    department_rows = (
        Department.objects
        .annotate(
            open=Count("tickets", filter=Q(tickets__status=Ticket.Status.OPEN)),
            in_progress=Count(
                "tickets", filter=Q(tickets__status=Ticket.Status.IN_PROGRESS)
            ),
            resolved=Count("tickets", filter=Q(tickets__status=Ticket.Status.RESOLVED)),
            cancelled=Count(
                "tickets", filter=Q(tickets__status=Ticket.Status.CANCELLED)
            ),
            total=Count("tickets"),
        )
        .order_by("name")
    )
    by_department = [
        {
            "department_id": dept.id,
            "department_name": dept.name,
            "open": dept.open,
            "in_progress": dept.in_progress,
            "resolved": dept.resolved,
            "cancelled": dept.cancelled,
            "total": dept.total,
        }
        for dept in department_rows
    ]

    window_start = timezone.now() - RESOLUTION_WINDOW
    avg_duration = (
        Ticket.objects
        .filter(
            status=Ticket.Status.RESOLVED,
            resolved_at__isnull=False,
            resolved_at__gte=window_start,
        )
        .annotate(
            resolution_time=ExpressionWrapper(
                F("resolved_at") - F("created_at"),
                output_field=DurationField(),
            )
        )
        .aggregate(avg=Avg("resolution_time"))["avg"]
    )
    avg_resolution_minutes = (
        round(avg_duration.total_seconds() / 60, 1) if avg_duration else None
    )

    # is_overdue depends on category.sla_minutes + "now" (a Python
    # property, not a DB column — see Ticket.is_overdue), so this can't
    # be a plain queryset filter. Same approach as
    # OperatorOverdueTicketCountView, just system-wide instead of scoped
    # to one department.
    open_tickets = (
        Ticket.objects
        .filter(status__in=[Ticket.Status.OPEN, Ticket.Status.IN_PROGRESS])
        .select_related("category")
    )
    overdue_count = sum(1 for ticket in open_tickets if ticket.is_overdue)

    return {
        "by_status": by_status,
        "by_department": by_department,
        "avg_resolution_minutes": avg_resolution_minutes,
        "overdue_count": overdue_count,
        "resolution_window_days": RESOLUTION_WINDOW.days,
        "generated_at": timezone.now(),
    }
