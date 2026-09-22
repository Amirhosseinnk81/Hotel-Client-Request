"""
IT Ops logic that isn't plain CRUD — kept out of the views, like
apps.tickets.services.

- mark_process_done()      Phase 4: carry out a recurring process; the next
                           due date follows from Process.save().
- compute_room_stats()     Phase 5: room occupancy for a day, from the real
- snapshot_room_stats()    Room data (live for today, RoomStatusLog for a
                           past day) — never typed in by hand.
- compute_today_dashboard() Phase 3: everything due today, in one call.
"""

from datetime import datetime, time, timedelta

from django.utils import timezone

from apps.rooms.models import Room, RoomStatusLog

from .models import DepartmentRequest, Process, RoomDailyStat, Task, priority_rank


def mark_process_done(process, at=None):
    """
    Record that `process` was carried out (now, unless `at` is given).
    For a recurring process Process.save() then moves next_due_at one
    period past this run.
    """
    process.last_done_at = at or timezone.now()
    process.save()
    return process


# -- room stats ---------------------------------------------------------------


def _end_of_day(day):
    """First instant of the next local day — status "at the end of `day`"."""
    return timezone.make_aware(datetime.combine(day + timedelta(days=1), time.min))


def _room_statuses_on(day):
    """
    {room_id: status} as it stood at the end of `day`.

    Today (or later) is simply the live Room.status. For a past day it is
    rebuilt from the append-only RoomStatusLog that Room.save() writes:
      - the room's last change up to that moment gives its status then;
      - with no change before it, the first change after it tells us what
        the status was before (its previous_status);
      - a room that never changed has always had its current status.
    Rooms are not dated, so every room that exists now is counted.
    """
    live = dict(Room.objects.values_list("id", "status"))
    if day >= timezone.localdate():
        return live

    cutoff = _end_of_day(day)
    statuses = dict(live)

    first_after = (
        RoomStatusLog.objects.filter(changed_at__gte=cutoff)
        .order_by("room_id", "changed_at", "id")
        .distinct("room_id")
        .values_list("room_id", "previous_status")
    )
    statuses.update(first_after)

    last_before = (
        RoomStatusLog.objects.filter(changed_at__lt=cutoff)
        .order_by("room_id", "-changed_at", "-id")
        .distinct("room_id")
        .values_list("room_id", "new_status")
    )
    statuses.update(last_before)

    return {room_id: status for room_id, status in statuses.items() if room_id in live}


def compute_room_stats(day=None):
    """Occupancy counts for `day` (default today), as a plain dict."""
    day = day or timezone.localdate()
    statuses = list(_room_statuses_on(day).values())
    return {
        "date": day,
        "total_rooms": len(statuses),
        "occupied_rooms": statuses.count(Room.Status.OCCUPIED),
        "vacant_rooms": statuses.count(Room.Status.AVAILABLE),
        "out_of_order_rooms": statuses.count(Room.Status.MAINTENANCE),
    }


def snapshot_room_stats(day=None):
    """
    Store (or refresh) the RoomDailyStat row for `day`. Safe to run more
    than once for the same day: the row is updated, never duplicated.
    Hand-written notes on an existing row are kept.
    """
    stats = compute_room_stats(day)
    day = stats.pop("date")
    snapshot, _created = RoomDailyStat.objects.update_or_create(date=day, defaults=stats)
    return snapshot


# -- today dashboard ----------------------------------------------------------


def compute_today_dashboard(user):
    """
    GET /it-ops/today/ — a single snapshot of today's IT workload:
      - tasks due today or overdue, not yet done
      - ACTIVE periodic processes due today or overdue (paused and
        archived ones are not due)
      - department requests still open, most urgent first
      - today's room occupancy, computed live (not the last stored row,
        which could be days old)
      - how many of the open tasks are the caller's own
    """
    now = timezone.localtime()
    end_of_today = _end_of_day(now.date())

    tasks = (
        Task.objects.filter(due_date__isnull=False, due_date__lt=end_of_today)
        .exclude(status=Task.Status.DONE)
        .select_related("assigned_to", "assigned_by")
        .annotate(priority_rank=priority_rank())
        .order_by("due_date", "-priority_rank")
    )

    processes = (
        Process.objects.filter(
            status=Process.Status.ACTIVE,
            next_due_at__isnull=False,
            next_due_at__lt=end_of_today,
        )
        .select_related("department", "responsible")
        .order_by("next_due_at")
    )

    open_requests = (
        DepartmentRequest.objects.filter(
            status__in=[DepartmentRequest.Status.PENDING, DepartmentRequest.Status.IN_PROGRESS]
        )
        .select_related("requesting_department", "assigned_to")
        .annotate(priority_rank=priority_rank())
        .order_by("-priority_rank", "created_at")
    )

    my_open_tasks = (
        Task.objects.filter(assigned_to=user).exclude(status=Task.Status.DONE).count()
    )

    return {
        "date": now.date(),
        "generated_at": timezone.now(),
        "tasks_due_or_overdue": tasks,
        "processes_due_or_overdue": processes,
        "open_department_requests": open_requests,
        "room_stats_today": compute_room_stats(now.date()),
        "my_open_tasks_count": my_open_tasks,
    }
