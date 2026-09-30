"""
The hotel's internal phone directory.

Ported from the separate Flask app `Hotel-extensions` ("سامانه داخلی‌های
هتل") so the hotel runs one system instead of two: one stack, one
database, one login, one deployment. The data model is the Flask one,
with two changes that only became possible by moving in here:

* `department` is a real `departments.Department` row rather than a
  table of free-text names of its own — the same single list of
  departments that tickets, operators and IT Ops already use (the same
  call made for IT Ops; see CLAUDE.md).
* who may read and change it comes from the platform's roles, so the
  Flask app's own users, login, secret admin URL and idle timeout are
  all gone.

Deleting is soft, as it was there: a directory is the sort of thing
somebody bulk-deletes by accident, and `Trash` in Django Admin can put
it back.
"""

from django.db import models
from django.utils import timezone


class ExtensionQuerySet(models.QuerySet):
    def alive(self):
        return self.filter(is_deleted=False)

    def deleted(self):
        return self.filter(is_deleted=True)


class Extension(models.Model):
    extension = models.CharField(
        max_length=20,
        unique=True,
        db_index=True,
        help_text="The internal number itself. Unique: importing the same number again updates that row.",
    )
    title = models.CharField(max_length=150, db_index=True, help_text="What this number is, e.g. «پذیرش».")
    person_name = models.CharField(max_length=150, blank=True, db_index=True)
    department = models.ForeignKey(
        "departments.Department",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="extensions",
    )
    location = models.CharField(max_length=150, blank=True)
    email = models.EmailField(max_length=150, blank=True)
    mobile = models.CharField(max_length=30, blank=True)
    notes = models.TextField(blank=True)

    is_active = models.BooleanField(
        default=True,
        db_index=True,
        help_text="Off for a number that exists but is out of use; it stays in the directory, marked inactive.",
    )
    is_deleted = models.BooleanField(default=False, db_index=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = ExtensionQuerySet.as_manager()

    class Meta:
        ordering = ["extension"]
        verbose_name = "Extension"
        verbose_name_plural = "Extensions"

    def __str__(self):
        return f"{self.extension} — {self.title}"

    def soft_delete(self):
        """To the trash, not gone: restorable from Django Admin."""
        self.is_deleted = True
        self.deleted_at = timezone.now()
        self.save(update_fields=["is_deleted", "deleted_at", "updated_at"])

    def restore(self):
        self.is_deleted = False
        self.deleted_at = None
        self.save(update_fields=["is_deleted", "deleted_at", "updated_at"])


class ExtensionActivity(models.Model):
    """
    Who changed the directory, and what they did — the Flask app's
    activity log, kept because a shared list that several people edit
    needs an answer to "who took that number out?".

    Written from the few places that change extensions (the API views,
    Django Admin, the importer) rather than from a signal, so the actor
    is actually known: a signal sees the row, not the person. Never
    edited or deleted; `actor` is the username as text so the log
    survives the user being removed.
    """

    class Action(models.TextChoices):
        CREATED = "CREATED", "Created"
        UPDATED = "UPDATED", "Updated"
        TRASHED = "TRASHED", "Moved to the trash"
        RESTORED = "RESTORED", "Restored"
        DELETED = "DELETED", "Deleted permanently"
        IMPORTED = "IMPORTED", "Imported"
        BACKED_UP = "BACKED_UP", "Backed up"

    actor = models.CharField(max_length=150, blank=True, help_text="Username, or empty for the system.")
    action = models.CharField(max_length=20, choices=Action.choices, db_index=True)
    label = models.CharField(max_length=200, help_text="What it happened to, e.g. «۲۱۰ — لباسشویی».")
    details = models.CharField(max_length=300, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Extension activity"
        verbose_name_plural = "Extension activity"

    def __str__(self):
        return f"{self.actor or 'system'} {self.action} {self.label}"
