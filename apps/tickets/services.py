"""
Ticket statistics and derived operator workload.

- compute_admin_stats_summary() — the whole hotel (Stage 2.4). Feeds the
  Django Admin "Stats Summary" page and GET /admin/stats/summary/, which
  the operator panel also shows to admins.
- compute_department_stats_summary(department) — one department. Feeds
  GET /operator/stats/summary/ for that department's operators and
  supervisor.
- active_tickets_count() / active_ticket_count(operator) — the single
  definition of an operator being "busy". Availability is derived from
  assignments rather than stored, and every surface that shows it counts
  through here.
- mark_operator_seen() / auto_assign() — presence ("panel open") and
  workload-based auto-assignment of new guest tickets.
- The two-stage SLA figures (first response, resolution) that both
  summaries report.

Plain functions (not tied to DRF or Django Admin) so every surface shares
one implementation instead of copies drifting apart.
"""

from datetime import timedelta

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import Avg, Count, DurationField, ExpressionWrapper, F, Q
from django.utils import timezone

from apps.departments.models import Department

from .models import Ticket, TicketAttachment, TicketHistory, TicketNote

# How far back "average resolution time" (and each operator's "resolved
# recently" count) looks. A fixed 30-day window rather than "all time" so
# the numbers reflect current operational performance, not diluted by
# however long the hotel has used the system.
RESOLUTION_WINDOW = timedelta(days=30)

ACTIVE_STATUSES = (Ticket.Status.OPEN, Ticket.Status.IN_PROGRESS)


def active_tickets_count():
    """
    Aggregate for a queryset of operators: how many tickets assigned to
    each are still OPEN or IN_PROGRESS, in that operator's own department.
    Use as `.annotate(active_tickets=active_tickets_count())`.

    This is THE definition of "busy": an operator is busy while it is
    above 0 and available at 0. There is no stored flag and no manual
    toggle, so it can't drift from reality — assigning a ticket makes the
    operator busy, resolving or cancelling their last one frees them, and a
    guest reopening a resolved ticket (which keeps its assignee) makes the
    same operator busy again, all without any code having to remember to
    update anything.

    The colleagues dropdown, the operator's own status
    (GET /operator/me/status/) and the department summary all count
    through here, so the three can never disagree.
    """
    return Count(
        "assigned_tickets",
        filter=Q(
            assigned_tickets__status__in=ACTIVE_STATUSES,
            assigned_tickets__department=F("department"),
        ),
    )


def active_ticket_count(operator):
    """The same count as active_tickets_count(), for a single operator."""
    return Ticket.objects.filter(
        assigned_to=operator,
        department=operator.department,
        status__in=ACTIVE_STATUSES,
    ).count()


# -- presence and auto-assignment ---------------------------------------------


def presence_window():
    return timedelta(seconds=getattr(settings, "OPERATOR_PRESENCE_SECONDS", 120))


def mark_operator_seen(user):
    """Record that this operator's panel is open right now (cheap UPDATE, no save())."""
    get_user_model().objects.filter(pk=user.pk).update(last_seen_at=timezone.now())


def pick_auto_assignee(department):
    """
    The operator a new ticket in `department` should go to, or None.

    Only operators whose panel is open count (last_seen_at within the
    presence window) — the system has no shift roster, and handing a
    ticket to someone who has gone home is worse than leaving it for the
    supervisor. Among those: fewest active tickets first (the same count as
    "busy"), then regular operators before the supervisor, who is also
    the one triaging.
    """
    return (
        get_user_model()
        .objects.filter(
            role="OPERATOR",
            is_active=True,
            department=department,
            last_seen_at__gte=timezone.now() - presence_window(),
        )
        .annotate(active_tickets=active_tickets_count())
        .order_by("active_tickets", "is_supervisor", "username")
        .first()
    )


def auto_assign(ticket):
    """
    Hand a new ticket to pick_auto_assignee() if its department has
    auto_assign on and nobody holds it yet. The ticket stays OPEN — the
    operator still has to start on it, which is what the first-response
    SLA measures. Logged as an ASSIGNED history entry with no user
    (the system did it). Returns the operator, or None.
    """
    if ticket.assigned_to_id is not None or not ticket.department.auto_assign:
        return None
    operator = pick_auto_assignee(ticket.department)
    if operator is None:
        return None

    ticket.assigned_to = operator
    ticket.save(update_fields=["assigned_to", "updated_at"])
    TicketHistory.objects.create(
        ticket=ticket,
        user=None,
        action=TicketHistory.Action.ASSIGNED,
        old_value=None,
        new_value=operator.username,
    )
    return operator


# -- duplicates -----------------------------------------------------------------


class MergeError(Exception):
    """A merge that breaks one of the rules below; the message says which."""


def merge_candidates(ticket):
    """Other still-open tickets from the same guest in the same department."""
    return (
        Ticket.objects.filter(
            guest_id=ticket.guest_id,
            department_id=ticket.department_id,
            status__in=ACTIVE_STATUSES,
        )
        .exclude(pk=ticket.pk)
        .select_related("category", "room", "assigned_to")
        .order_by("created_at")
    )


@transaction.atomic
def merge_tickets(source, target, user):
    """
    Fold duplicate `source` into `target` (inspired by Odoo Helpdesk's
    ticket merge). A guest who asks for towels twice gets one ticket, one
    operator on it, and one set of numbers in the reports.

    Rules: same guest and same department (different guests asking for the
    same thing are different requests); the duplicate must still be OPEN
    (once someone has started on it, it isn't a stray duplicate any more);
    the target must still be open (OPEN or IN_PROGRESS).

    Effect: the duplicate is CANCELLED with merged_into set, its photos move
    to the target, both timelines record the merge, and the target gets an
    internal note quoting the duplicate. No cancellation SMS goes out — the
    guest's request is still being handled, under the other number.
    """
    if source.pk == target.pk:
        raise MergeError("A ticket cannot be merged into itself.")
    if source.guest_id != target.guest_id or source.department_id != target.department_id:
        raise MergeError("Only tickets from the same guest in the same department can be merged.")
    if source.status != Ticket.Status.OPEN:
        raise MergeError("Only a ticket nobody has started on (OPEN) can be merged away.")
    if target.status not in ACTIVE_STATUSES:
        raise MergeError("The ticket to merge into must still be open.")

    source.status = Ticket.Status.CANCELLED
    source.merged_into = target
    source.save(update_fields=["status", "merged_into", "updated_at"])

    TicketAttachment.objects.filter(ticket=source).update(ticket=target)
    TicketNote.objects.create(
        ticket=target,
        author=user,
        text=f"درخواست تکراری #{source.pk} («{source.title}») با این درخواست ادغام شد.\n{source.description}",
    )
    TicketHistory.objects.create(
        ticket=source,
        user=user,
        action=TicketHistory.Action.MERGED,
        old_value=str(source.pk),
        new_value=str(target.pk),
    )
    TicketHistory.objects.create(
        ticket=target,
        user=user,
        action=TicketHistory.Action.MERGED,
        old_value=str(source.pk),
        new_value=str(target.pk),
    )
    target.save(update_fields=["updated_at"])
    return target


# -- statistics -----------------------------------------------------------------


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


def _percent(met, due):
    return round(met / due * 100, 1) if due else None


def _sla_performance(tickets, window_start):
    """
    Two-stage SLA over the tickets created in the window:

    - first response: responded in time / all that were due (responded,
      or still waiting past the deadline). A ticket cancelled before
      anyone started on it is not counted either way.
    - resolution: resolved in time / all that were due (resolved, or
      still active past the deadline).

    Plus the average time to first response, and — for right now, not the
    window — how many tickets are still waiting past their response target.
    Computed in Python off each ticket's own deadline properties, so the
    SLA rules stay defined in one place (the model), like _overdue_count.
    """
    now = timezone.now()
    response_met = response_due = resolution_met = resolution_due = 0
    response_minutes = []

    for ticket in tickets.filter(created_at__gte=window_start).select_related("category"):
        if ticket.first_response_at is not None:
            response_due += 1
            response_met += ticket.first_response_at <= ticket.response_deadline
            response_minutes.append((ticket.first_response_at - ticket.created_at).total_seconds() / 60)
        elif ticket.status == Ticket.Status.OPEN and now > ticket.response_deadline:
            response_due += 1

        if ticket.status == Ticket.Status.RESOLVED and ticket.resolved_at is not None:
            resolution_due += 1
            resolution_met += ticket.resolved_at <= ticket.sla_deadline
        elif ticket.status in ACTIVE_STATUSES and now > ticket.sla_deadline:
            resolution_due += 1

    waiting = tickets.filter(status=Ticket.Status.OPEN, first_response_at__isnull=True).select_related(
        "category"
    )
    return {
        "avg_first_response_minutes": (
            round(sum(response_minutes) / len(response_minutes), 1) if response_minutes else None
        ),
        "response_sla_met_percent": _percent(response_met, response_due),
        "resolution_sla_met_percent": _percent(resolution_met, resolution_due),
        "response_overdue_count": sum(1 for ticket in waiting if ticket.is_response_overdue),
    }


def _ratings(tickets, window_start):
    """
    Guest satisfaction over the window (inspired by Odoo Helpdesk's
    customer-ratings report): average of the 1-5 stars, how many ratings,
    the spread per star, and the latest written comments. A rating belongs
    to the window its ticket was resolved in (there's no separate rated-at).
    """
    rated = tickets.filter(guest_rating__isnull=False, resolved_at__gte=window_start)
    totals = rated.aggregate(avg=Avg("guest_rating"), count=Count("id"))
    distribution = {str(stars): 0 for stars in range(1, 6)}
    for row in rated.values("guest_rating").annotate(n=Count("id")):
        distribution[str(row["guest_rating"])] = row["n"]

    recent = (
        rated.exclude(guest_feedback="")
        .select_related("assigned_to", "department")
        .order_by("-resolved_at")[:5]
    )
    return {
        "rating_avg": round(totals["avg"], 2) if totals["avg"] is not None else None,
        "rating_count": totals["count"],
        "rating_distribution": distribution,
        "recent_feedback": [
            {
                "ticket_id": ticket.id,
                "title": ticket.title,
                "rating": ticket.guest_rating,
                "feedback": ticket.guest_feedback,
                "operator": ticket.assigned_to.username if ticket.assigned_to_id else None,
                "department_name": ticket.department.name,
                "resolved_at": ticket.resolved_at,
            }
            for ticket in recent
        ],
    }


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
            rating_avg=Avg(
                "tickets__guest_rating",
                filter=Q(tickets__guest_rating__isnull=False, tickets__resolved_at__gte=window_start),
            ),
            rating_count=Count(
                "tickets",
                filter=Q(tickets__guest_rating__isnull=False, tickets__resolved_at__gte=window_start),
            ),
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
                "rating_avg": round(dept.rating_avg, 2) if dept.rating_avg is not None else None,
                "rating_count": dept.rating_count,
            }
            for dept in department_rows
        ],
        "avg_resolution_minutes": _avg_resolution_minutes(tickets, window_start),
        "overdue_count": _overdue_count(tickets),
        **_sla_performance(tickets, window_start),
        **_ratings(tickets, window_start),
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
    # Both counts stay in ONE annotate() call over the same relation so
    # Django uses a single join for them.
    operators = (
        get_user_model().objects
        .filter(role="OPERATOR", department=department)
        .annotate(
            active_tickets=active_tickets_count(),
            resolved_recent=Count(
                "assigned_tickets",
                filter=Q(
                    assigned_tickets__department=department,
                    assigned_tickets__status=Ticket.Status.RESOLVED,
                    assigned_tickets__resolved_at__gte=window_start,
                ),
            ),
            rating_avg=Avg(
                "assigned_tickets__guest_rating",
                filter=Q(
                    assigned_tickets__department=department,
                    assigned_tickets__guest_rating__isnull=False,
                    assigned_tickets__resolved_at__gte=window_start,
                ),
            ),
            rating_count=Count(
                "assigned_tickets",
                filter=Q(
                    assigned_tickets__department=department,
                    assigned_tickets__guest_rating__isnull=False,
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
                "active": operator.active_tickets,
                "resolved_recent": operator.resolved_recent,
                "rating_avg": round(operator.rating_avg, 2) if operator.rating_avg is not None else None,
                "rating_count": operator.rating_count,
            }
            for operator in operators
        ],
        "avg_resolution_minutes": _avg_resolution_minutes(tickets, window_start),
        "overdue_count": _overdue_count(tickets),
        **_sla_performance(tickets, window_start),
        **_ratings(tickets, window_start),
        "resolution_window_days": RESOLUTION_WINDOW.days,
        "generated_at": timezone.now(),
    }
