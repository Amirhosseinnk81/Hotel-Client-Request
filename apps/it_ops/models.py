import calendar
from datetime import timedelta

from django.conf import settings
from django.db import models
from django.db.models import Case, IntegerField, Value, When
from django.utils import timezone


class Priority(models.TextChoices):
    LOW = "LOW", "Low"
    MEDIUM = "MEDIUM", "Medium"
    HIGH = "HIGH", "High"
    CRITICAL = "CRITICAL", "Critical"


def priority_rank(field="priority"):
    """
    Sort key for Priority: CRITICAL=4 ... LOW=1. Order with
    `.annotate(priority_rank=priority_rank()).order_by("-priority_rank", ...)`.

    Needed because the values are strings: a plain order_by("-priority")
    sorts them alphabetically, which puts MEDIUM first and CRITICAL last.
    """
    return Case(
        When(**{field: Priority.CRITICAL}, then=Value(4)),
        When(**{field: Priority.HIGH}, then=Value(3)),
        When(**{field: Priority.MEDIUM}, then=Value(2)),
        When(**{field: Priority.LOW}, then=Value(1)),
        default=Value(0),
        output_field=IntegerField(),
    )


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


def _add_months(moment, months):
    """moment + N calendar months, clamping the day (Jan 31 + 1 month = Feb 28/29)."""
    month_index = moment.month - 1 + months
    year = moment.year + month_index // 12
    month = month_index % 12 + 1
    day = min(moment.day, calendar.monthrange(year, month)[1])
    return moment.replace(year=year, month=month, day=day)


class Process(TimeStampedModel):
    """
    Any recurring or standing piece of IT work: active workflows, passive
    monitoring, periodic checks, and periodic services (maintenance).
    """

    class ProcessType(models.TextChoices):
        ACTIVE = "ACTIVE", "Active"
        PASSIVE = "PASSIVE", "Passive"
        PERIODIC_CHECK = "PERIODIC_CHECK", "Periodic Check"
        PERIODIC_SERVICE = "PERIODIC_SERVICE", "Periodic Service"

    class Frequency(models.TextChoices):
        NONE = "NONE", "N/A"
        DAILY = "DAILY", "Daily"
        WEEKLY = "WEEKLY", "Weekly"
        MONTHLY = "MONTHLY", "Monthly"
        QUARTERLY = "QUARTERLY", "Quarterly"
        YEARLY = "YEARLY", "Yearly"

    class Status(models.TextChoices):
        ACTIVE = "ACTIVE", "Active"
        PAUSED = "PAUSED", "Paused"
        ARCHIVED = "ARCHIVED", "Archived"

    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    process_type = models.CharField(max_length=20, choices=ProcessType.choices)
    department = models.ForeignKey(
        "departments.Department",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="it_processes",
        help_text="The hotel department this process serves (blank = IT itself).",
    )
    frequency = models.CharField(
        max_length=10, choices=Frequency.choices, default=Frequency.NONE
    )
    status = models.CharField(
        max_length=10, choices=Status.choices, default=Status.ACTIVE
    )
    responsible = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="owned_processes",
    )
    last_done_at = models.DateTimeField(null=True, blank=True)
    next_due_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text=(
            "Filled in automatically for recurring processes: last_done_at "
            "(or creation) plus one period. May be moved by hand to postpone "
            "a run; recalculated whenever the process is marked done or its "
            "frequency changes."
        ),
    )

    class Meta:
        ordering = ["next_due_at", "title"]

    def __str__(self):
        return f"[{self.get_process_type_display()}] {self.title}"

    def next_due_after(self, moment):
        """One period after `moment`, or None for a non-recurring process."""
        if self.frequency == self.Frequency.DAILY:
            return moment + timedelta(days=1)
        if self.frequency == self.Frequency.WEEKLY:
            return moment + timedelta(weeks=1)
        if self.frequency == self.Frequency.MONTHLY:
            return _add_months(moment, 1)
        if self.frequency == self.Frequency.QUARTERLY:
            return _add_months(moment, 3)
        if self.frequency == self.Frequency.YEARLY:
            return _add_months(moment, 12)
        return None

    def save(self, *args, **kwargs):
        """
        Phase 4 — keep next_due_at in step with the schedule. Done in save()
        rather than a signal, like Room.save() writing RoomStatusLog, so the
        rule holds for every write path (API, Django Admin, shell).

        For a recurring process, next_due_at is recalculated when:
          - it is empty,
          - last_done_at moved (the process was just carried out), or
          - the frequency changed.
        Otherwise a hand-set next_due_at (a postponed run) is left alone.
        A non-recurring process (frequency NONE) is never touched: its
        next_due_at, if any, is a one-off date set by hand.
        """
        previous = None
        if self.pk is not None:
            previous = (
                Process.objects.filter(pk=self.pk)
                .values("last_done_at", "frequency")
                .first()
            )

        if self.frequency != self.Frequency.NONE:
            done_moved = previous is not None and previous["last_done_at"] != self.last_done_at
            frequency_changed = previous is not None and previous["frequency"] != self.frequency
            if self.next_due_at is None or done_moved or frequency_changed:
                self.next_due_at = self.next_due_after(self.last_done_at or timezone.now())

        super().save(*args, **kwargs)

    @property
    def is_overdue(self):
        return bool(
            self.status == self.Status.ACTIVE
            and self.next_due_at is not None
            and self.next_due_at < timezone.now()
        )


class Project(TimeStampedModel):
    class Status(models.TextChoices):
        PLANNING = "PLANNING", "Planning"
        IN_PROGRESS = "IN_PROGRESS", "In Progress"
        ON_HOLD = "ON_HOLD", "On Hold"
        DONE = "DONE", "Done"
        CANCELLED = "CANCELLED", "Cancelled"

    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    status = models.CharField(
        max_length=15, choices=Status.choices, default=Status.PLANNING
    )
    priority = models.CharField(
        max_length=10, choices=Priority.choices, default=Priority.MEDIUM
    )
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="owned_projects",
    )
    start_date = models.DateField(null=True, blank=True)
    due_date = models.DateField(null=True, blank=True)

    class Meta:
        # Priority order is applied in the views via priority_rank(); a
        # Meta ordering on the string field would sort alphabetically.
        ordering = ["due_date", "title"]

    def __str__(self):
        return self.title


class DepartmentRequest(TimeStampedModel):
    """
    Work another hotel department asks of IT (new PC, printer, access...).
    Staff-to-IT, not guest-facing: guest requests stay in apps.tickets.
    """

    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        IN_PROGRESS = "IN_PROGRESS", "In Progress"
        COMPLETED = "COMPLETED", "Completed"
        REJECTED = "REJECTED", "Rejected"

    CLOSED_STATUSES = (Status.COMPLETED, Status.REJECTED)

    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    requesting_department = models.ForeignKey(
        "departments.Department",
        on_delete=models.PROTECT,
        # Nullable only for rows migrated from the old free-text choice list
        # that matched no real department; the API requires it.
        null=True,
        related_name="it_requests",
    )
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="it_requests_filed",
        help_text=(
            "The operator who filed it from their own department's panel. "
            "Empty when IT logged a phoned-in request (see requested_by_name)."
        ),
    )
    requested_by_name = models.CharField(
        max_length=150,
        blank=True,
        help_text="Name of the person who filed the request, if not a system user.",
    )
    priority = models.CharField(
        max_length=10, choices=Priority.choices, default=Priority.MEDIUM
    )
    status = models.CharField(
        max_length=15, choices=Status.choices, default=Status.PENDING
    )
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_department_requests",
    )
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"{self.requesting_department}: {self.title}"

    def save(self, *args, **kwargs):
        # resolved_at follows the status, whichever path changed it.
        if self.status in self.CLOSED_STATUSES:
            if self.resolved_at is None:
                self.resolved_at = timezone.now()
        else:
            self.resolved_at = None
        super().save(*args, **kwargs)


class Goal(TimeStampedModel):
    class GoalType(models.TextChoices):
        SHORT_TERM = "SHORT_TERM", "Short Term"
        LONG_TERM = "LONG_TERM", "Long Term"

    class Status(models.TextChoices):
        NOT_STARTED = "NOT_STARTED", "Not Started"
        IN_PROGRESS = "IN_PROGRESS", "In Progress"
        ACHIEVED = "ACHIEVED", "Achieved"
        MISSED = "MISSED", "Missed"

    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    goal_type = models.CharField(max_length=15, choices=GoalType.choices)
    status = models.CharField(
        max_length=15, choices=Status.choices, default=Status.NOT_STARTED
    )
    target_date = models.DateField(null=True, blank=True)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="owned_goals",
    )
    related_project = models.ForeignKey(
        Project,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="goals",
    )

    class Meta:
        ordering = ["goal_type", "target_date"]

    def __str__(self):
        return f"[{self.get_goal_type_display()}] {self.title}"


class Task(TimeStampedModel):
    class Status(models.TextChoices):
        TODO = "TODO", "To Do"
        IN_PROGRESS = "IN_PROGRESS", "In Progress"
        DONE = "DONE", "Done"
        BLOCKED = "BLOCKED", "Blocked"

    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    status = models.CharField(
        max_length=15, choices=Status.choices, default=Status.TODO
    )
    priority = models.CharField(
        max_length=10, choices=Priority.choices, default=Priority.MEDIUM
    )
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_tasks",
    )
    assigned_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="tasks_created",
    )
    due_date = models.DateTimeField(null=True, blank=True)

    # Optional links back to the thing this task belongs to.
    related_process = models.ForeignKey(
        Process, on_delete=models.SET_NULL, null=True, blank=True, related_name="tasks"
    )
    related_project = models.ForeignKey(
        Project, on_delete=models.SET_NULL, null=True, blank=True, related_name="tasks"
    )
    related_request = models.ForeignKey(
        DepartmentRequest,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="tasks",
    )

    class Meta:
        ordering = ["due_date", "created_at"]

    def __str__(self):
        return self.title


class RoomDailyStat(models.Model):
    """
    Daily snapshot of room occupancy, computed from the real Room data
    (apps.it_ops.services.snapshot_room_stats) — never typed in by hand.
    Today's snapshot comes from live Room.status; a past day is rebuilt
    from RoomStatusLog. Written by the `snapshot_room_stats` management
    command (run nightly by Windows Task Scheduler) or the
    POST /it-ops/room-stats/snapshot/ action.
    """

    date = models.DateField(unique=True)
    total_rooms = models.PositiveIntegerField()
    occupied_rooms = models.PositiveIntegerField(default=0)
    vacant_rooms = models.PositiveIntegerField(default=0)
    out_of_order_rooms = models.PositiveIntegerField(default=0)
    notes = models.TextField(blank=True)
    # auto_now: re-snapshotting a day updates the row, so this is "last computed".
    recorded_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-date"]

    @property
    def occupancy_rate(self):
        if not self.total_rooms:
            return 0
        return round((self.occupied_rooms / self.total_rooms) * 100, 1)

    def __str__(self):
        return f"{self.date} — {self.occupancy_rate}% occupied"
