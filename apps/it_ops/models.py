from django.conf import settings
from django.db import models


class Department(models.TextChoices):
    IT = "IT", "IT"
    FRONT_DESK = "FRONT_DESK", "Front Desk"
    HOUSEKEEPING = "HOUSEKEEPING", "Housekeeping"
    MAINTENANCE = "MAINTENANCE", "Maintenance"
    FOOD_AND_BEVERAGE = "F_AND_B", "Food & Beverage"
    SALES = "SALES", "Sales"
    HR = "HR", "HR"
    FINANCE = "FINANCE", "Finance"
    MANAGEMENT = "MANAGEMENT", "Management"
    OTHER = "OTHER", "Other"


class Priority(models.TextChoices):
    LOW = "LOW", "Low"
    MEDIUM = "MEDIUM", "Medium"
    HIGH = "HIGH", "High"
    CRITICAL = "CRITICAL", "Critical"


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


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
    department = models.CharField(
        max_length=20, choices=Department.choices, default=Department.IT
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
    next_due_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["next_due_at", "title"]

    def __str__(self):
        return f"[{self.get_process_type_display()}] {self.title}"


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
        ordering = ["-priority", "due_date"]

    def __str__(self):
        return self.title


class DepartmentRequest(TimeStampedModel):
    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        IN_PROGRESS = "IN_PROGRESS", "In Progress"
        COMPLETED = "COMPLETED", "Completed"
        REJECTED = "REJECTED", "Rejected"

    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    requesting_department = models.CharField(
        max_length=20, choices=Department.choices
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
        ordering = ["-priority", "created_at"]

    def __str__(self):
        return f"{self.requesting_department}: {self.title}"


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
        ordering = ["-priority", "due_date"]

    def __str__(self):
        return self.title


class RoomDailyStat(models.Model):
    """
    Daily snapshot of room status. Can be filled manually for now and later
    synced automatically from the Room model in the guest-request backend.
    """

    date = models.DateField(unique=True)
    total_rooms = models.PositiveIntegerField()
    occupied_rooms = models.PositiveIntegerField(default=0)
    vacant_rooms = models.PositiveIntegerField(default=0)
    out_of_order_rooms = models.PositiveIntegerField(default=0)
    notes = models.TextField(blank=True)
    recorded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-date"]

    @property
    def occupancy_rate(self):
        if not self.total_rooms:
            return 0
        return round((self.occupied_rooms / self.total_rooms) * 100, 1)

    def __str__(self):
        return f"{self.date} — {self.occupancy_rate}% occupied"
