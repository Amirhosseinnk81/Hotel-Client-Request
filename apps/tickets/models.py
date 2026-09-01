from datetime import timedelta

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import (
    FileExtensionValidator,
    MaxValueValidator,
    MinValueValidator,
)
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

    # --- Guest experience (Stage 2.3) ----------------------------------

    guest_rating = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        help_text="1-5 stars, set once by the guest after the ticket is RESOLVED.",
    )

    guest_feedback = models.TextField(
        blank=True,
        default="",
    )

    reopened_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text=(
            "Set the one time (if ever) a guest reopens this ticket. "
            "Presence of a value — not just the current status — is what "
            "blocks a second reopen, so the limit holds even if the "
            "ticket gets resolved again afterwards."
        ),
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"#{self.pk} - {self.title}"

    # --- Guest reopen (Stage 2.3) ---------------------------------------
    # Deliberately NOT part of ALLOWED_STATUS_TRANSITIONS / can_transition_to
    # above: those govern the general operator-facing PATCH endpoint, and
    # RESOLVED must stay terminal there. Reopening is a narrower, guest-only
    # action with its own time limit and one-time-only rule, enforced here
    # and only reachable through the dedicated reopen endpoint.
    REOPEN_WINDOW = timedelta(hours=48)

    @property
    def can_guest_reopen(self):
        if self.status != self.Status.RESOLVED:
            return False
        if self.reopened_at is not None:
            return False
        if self.resolved_at is None:
            return False
        return timezone.now() <= self.resolved_at + self.REOPEN_WINDOW
    
    
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

class QuickRequestTemplate(models.Model):
    """
    A one-click shortcut on the guest's "new ticket" form (Stage 2.3) —
    e.g. "Towels", "Extra pillow", "Room service menu". Picking one
    pre-fills title/department/category on the form; the guest can still
    edit everything before submitting. Managed entirely from Django Admin
    — there's no guest-facing create/edit, only GET /quick-templates/.
    """

    title = models.CharField(max_length=100)

    icon = models.CharField(
        max_length=50,
        help_text=(
            "A lucide-react icon name (e.g. 'Droplet', 'Shirt', 'Bell') — "
            "the frontend renders this icon on the card. Not validated "
            "here; an unknown name just falls back to a generic icon."
        ),
    )

    department = models.ForeignKey(
        Department,
        on_delete=models.CASCADE,
        related_name="quick_templates",
    )

    category = models.ForeignKey(
        Category,
        on_delete=models.CASCADE,
        related_name="quick_templates",
    )

    is_active = models.BooleanField(default=True)

    order = models.PositiveIntegerField(
        default=0,
        help_text="Lower numbers show first on the guest form.",
    )

    class Meta:
        ordering = ["order", "title"]

    def __str__(self):
        return self.title


def validate_attachment_size(file):
    """Rejects uploads over MAX_ATTACHMENT_SIZE_MB (default 5MB, env-tunable)."""
    max_bytes = settings.MAX_ATTACHMENT_SIZE_MB * 1024 * 1024
    if file.size > max_bytes:
        raise ValidationError(
            f"File too large ({file.size / 1024 / 1024:.1f}MB). "
            f"Max size is {settings.MAX_ATTACHMENT_SIZE_MB}MB."
        )


def ticket_attachment_upload_path(instance, filename):
    return f"ticket_attachments/{instance.ticket_id}/{filename}"


class TicketAttachment(models.Model):
    """
    An image attached to a ticket (Stage 2.8) — either a guest's photo of
    the problem (attached at creation or later) or an operator's photo of
    the fix (attached before resolving). Local disk storage under
    MEDIA_ROOT only; no S3/MinIO in this phase.
    """

    ticket = models.ForeignKey(
        Ticket,
        on_delete=models.CASCADE,
        related_name="attachments",
    )

    image = models.ImageField(
        upload_to=ticket_attachment_upload_path,
        validators=[
            FileExtensionValidator(
                allowed_extensions=["jpg", "jpeg", "png", "webp", "gif"]
            ),
            validate_attachment_size,
        ],
        help_text="Image only (jpg/jpeg/png/webp/gif), max MAX_ATTACHMENT_SIZE_MB.",
    )

    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="ticket_attachments",
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"Attachment #{self.pk} on Ticket #{self.ticket_id}"