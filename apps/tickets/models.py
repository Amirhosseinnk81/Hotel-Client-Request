from django.conf import settings
from django.db import models

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