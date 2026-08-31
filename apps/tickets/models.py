from datetime import timedelta

from django.conf import settings
from django.db import models
from django.utils import timezone

from apps.departments.models import Department
from apps.guests.models import Guest
from apps.rooms.models import Room


class Category(models.Model):
    """
    Ticket category (Housekeeping, Maintenance, IT, Reception, Room
    Service, Laundry, ...). Chosen by the guest when creating a ticket.
    Routing to a department is fully manual in this MVP (no AI).
    """

    name = models.CharField(max_length=100, unique=True)
    code = models.CharField(max_length=50, unique=True)
    is_active = models.BooleanField(default=True)
    sla_minutes = models.PositiveIntegerField(
        default=60,
        help_text=(
            "Expected response time for a ticket in this category, in "
            "minutes (e.g. towels: 15, power outage: 10). Drives both the "
            "guest-facing \"estimated response time\" and the operator "
            "overdue highlight — there is deliberately only one number to "
            "configure, not a separate one for each."
        ),
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "Category"
        verbose_name_plural = "Categories"

    def __str__(self):
        return self.name


class Ticket(models.Model):

    class Status(models.TextChoices):
        OPEN = "OPEN", "Open"
        IN_PROGRESS = "IN_PROGRESS", "In Progress"
        RESOLVED = "RESOLVED", "Resolved"
        CANCELLED = "CANCELLED", "Cancelled"

    class Priority(models.TextChoices):
        LOW = "LOW", "Low"
        NORMAL = "NORMAL", "Normal"
        HIGH = "HIGH", "High"
        URGENT = "URGENT", "Urgent"
        
    ALLOWED_STATUS_TRANSITIONS = {
        Status.OPEN: {
            Status.IN_PROGRESS,
            Status.CANCELLED,
        },
        Status.IN_PROGRESS: {
            Status.OPEN,
            Status.RESOLVED,
        },
        Status.RESOLVED: set(),
        Status.CANCELLED: set(),
    }

    def can_transition_to(self, new_status):
        return new_status in self.ALLOWED_STATUS_TRANSITIONS.get(
            self.status,
            set(),
        )

    # --- SLA (Stage 2.9) ----------------------------------------------
    # A ticket is "overdue" once it's been open longer than its category's
    # configured sla_minutes, and only while it's still actionable (a
    # RESOLVED/CANCELLED ticket is never overdue, no matter how long ago
    # it closed — there's nothing left to breach). Deliberately a single
    # sla_minutes-per-category knob, not a separate per-priority table:
    # it's also what the guest-facing "estimated response time" reads, so
    # there's exactly one number to keep in sync, not two.

    @property
    def sla_deadline(self):
        return self.created_at + timedelta(minutes=self.category.sla_minutes)

    @property
    def is_overdue(self):
        if self.status not in (self.Status.OPEN, self.Status.IN_PROGRESS):
            return False
        return timezone.now() > self.sla_deadline

    @property
    def overdue_since(self):
        return self.sla_deadline if self.is_overdue else None

    guest = models.ForeignKey(
        Guest,
        on_delete=models.CASCADE,
        related_name="tickets",
    )

    room = models.ForeignKey(
        Room,
        on_delete=models.PROTECT,
        related_name="tickets",
        help_text="Snapshot of the guest's room at the time the ticket was created.",
    )

    department = models.ForeignKey(
        Department,
        on_delete=models.PROTECT,
        related_name="tickets",
    )

    category = models.ForeignKey(
        Category,
        on_delete=models.PROTECT,
        related_name="tickets",
    )

    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_tickets",
        limit_choices_to={"role": "OPERATOR"},
    )

    title = models.CharField(
        max_length=200,
    )

    description = models.TextField()

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.OPEN,
        db_index=True,
    )

    priority = models.CharField(
        max_length=10,
        choices=Priority.choices,
        default=Priority.NORMAL,
    )

    resolution = models.TextField(
        null=True,
        blank=True,
        help_text="Filled in by the operator when resolving the ticket.",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    resolved_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"#{self.pk} - {self.title}"
    
    
class TicketHistory(models.Model):

    class Action(models.TextChoices):
        CREATED = "CREATED", "Created"
        UPDATED = "UPDATED", "Updated"
        ASSIGNED = "ASSIGNED", "Assigned"
        STATUS_CHANGED = "STATUS_CHANGED", "Status Changed"
        PRIORITY_CHANGED = "PRIORITY_CHANGED", "Priority Changed"

    ticket = models.ForeignKey(
        Ticket,
        on_delete=models.CASCADE,
        related_name="history",
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="ticket_history",
    )

    action = models.CharField(
        max_length=30,
        choices=Action.choices,
    )

    old_value = models.TextField(
        null=True,
        blank=True,
    )

    new_value = models.TextField(
        null=True,
        blank=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"Ticket #{self.ticket_id} - {self.action}"


class TicketNote(models.Model):
    """
    An internal note left by an operator/admin on a ticket.

    Kept as a separate model from TicketHistory (rather than an
    action=NOTE entry) because notes carry free-form text authored by a
    person, while TicketHistory rows are short system-generated audit
    entries (old_value -> new_value). The two are merged into a single
    chronological timeline at the API layer.

    Guests must never see these — enforced at the view/permission layer,
    not here.
    """

    ticket = models.ForeignKey(
        Ticket,
        on_delete=models.CASCADE,
        related_name="notes",
    )

    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="ticket_notes",
    )

    text = models.TextField()

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"Note on Ticket #{self.ticket_id} by {self.author}"