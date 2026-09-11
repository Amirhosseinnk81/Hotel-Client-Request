"""
Ticket statistics — the numbers behind every Stats Summary surface.

Two entry points, each with one fixed scope:

- compute_admin_stats_summary() — the whole hotel (Stage 2.4). Feeds the
  Django Admin "Stats Summary" page and GET /admin/stats/summary/, which
  the operator panel also shows to admins.
- compute_department_stats_summary(department) — one department. Feeds
  GET /operator/stats/summary/ for that department's operators and
  supervisor.

Plain functions (not tied to DRF or Django Admin) so every surface shares
one implementation instead of copies drifting apart. The per-status,
average-resolution and overdue maths lives in one set of helpers that
each scope runs over its own queryset.
"""

from datetime import timedelta

from django.contrib.auth import get_user_model
from django.db.models import Avg, Count, DurationField, ExpressionWrapper, F, Q
from django.utils import timezone

from apps.departments.models import Department

from .models import Ticket

# How far back "average resolution time" (and each operator's "resolved
# recently" count) looks. A fixed 30-day window rather than "all time" so
# the numbers reflect current operational performance, not diluted by
# however long the hotel has used the system.
RESOLUTION_WINDOW = timedelta(days=30)

ACTIVE_STATUSES = (Ticket.Status.OPEN, Ticket.Status.IN_PROGRESS)


def _by_status(tickets):
    counts = {
        row["status"]: row["count"]
        for row in tickets.values("status").annotate(count=Count("id"))
    }
    # Every status key is always present (0 rather than missing) so the
    # frontend/template never has to guess-and-default.
    return {value: counts.get(value, 0) for value, _label in Ticket.Status.choices}


def _avg_resolution_minutes(tickets, window_start):
    avg_duration = (
        tickets
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
    return round(avg_duration.total_seconds() / 60, 1) if avg_duration else None


def _overdue_count(tickets):
    # is_overdue depends on category.sla_minutes + "now" (a Python
    # property, not a DB column — see Ticket.is_overdue), so this can't be
    # a plain queryset filter. Same approach as
    # OperatorOverdueTicketCountView: load the still-open tickets and let
    # the model decide, so the overdue rule stays defined in one place.
    open_tickets = tickets.filter(status__in=ACTIVE_STATUSES).select_related("category")
    return sum(1 for ticket in open_tickets if ticket.is_overdue)


def compute_admin_stats_summary():
    tickets = Ticket.objects.all()
    window_start = timezone.now() - RESOLUTION_WINDOW

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

    return {
        "by_status": _by_status(tickets),
        "by_department": [
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
        ],
        "avg_resolution_minutes": _avg_resolution_minutes(tickets, window_start),
        "overdue_count": _overdue_count(tickets),
        "resolution_window_days": RESOLUTION_WINDOW.days,
        "generated_at": timezone.now(),
    }


def compute_department_stats_summary(department):
    # Refuse rather than default: "no department" must never quietly turn
    # into "every department". An operator without a department is a
    # misconfigured account, and the caller decides what to do about it
    # (DepartmentStatsSummaryView answers 403).
    if department is None:
        raise ValueError("compute_department_stats_summary() needs a department.")

    tickets = Ticket.objects.filter(department=department)
    window_start = timezone.now() - RESOLUTION_WINDOW

    # The department's whole roster, not just whoever currently holds a
    # ticket, so an idle operator still shows up with 0 — that's exactly
    # the person a supervisor is looking for. Supervisors listed first.
    in_department = Q(assigned_tickets__department=department)
    operators = (
        get_user_model().objects
        .filter(role="OPERATOR", department=department)
        .annotate(
            active=Count(
                "assigned_tickets",
                filter=in_department & Q(assigned_tickets__status__in=ACTIVE_STATUSES),
            ),
            resolved_recent=Count(
                "assigned_tickets",
                filter=in_department
                & Q(
                    assigned_tickets__status=Ticket.Status.RESOLVED,
                    assigned_tickets__resolved_at__gte=window_start,
                ),
            ),
        )
        .order_by("-is_supervisor", "username")
    )

    return {
        "department_id": department.id,
        "department_name": department.name,
        "by_status": _by_status(tickets),
        "by_operator": [
            {
                "operator_id": operator.id,
                "username": operator.username,
                "is_supervisor": operator.is_supervisor,
                "active": operator.active,
                "resolved_recent": operator.resolved_recent,
            }
            for operator in operators
        ],
        "avg_resolution_minutes": _avg_resolution_minutes(tickets, window_start),
        "overdue_count": _overdue_count(tickets),
        "resolution_window_days": RESOLUTION_WINDOW.days,
        "generated_at": timezone.now(),
    }
