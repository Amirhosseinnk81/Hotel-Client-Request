"""
Hotel news and events — what the hotel wants to tell people.

Two audiences out of one table: what the guest sees on their portal and
on the room TV (tonight's live music, the pool closing for cleaning) and
what the staff sees in the panel (a shift briefing, a VIP arriving).
They are the same object with the same publish window and the same
Django Admin page; splitting them would mean writing the window and the
ordering twice, and the difference between them is one field.

Bilingual like the guest portal (`apps/guests.HotelInfo`): the English
fields are optional and fall back to the Persian ones. Staff-only items
never need them — the panel is Persian on purpose.
"""

from django.db import models
from django.utils import timezone


class NewsItemQuerySet(models.QuerySet):
    def published(self, now=None):
        """
        Active, already started, not yet finished.

        The window is the only thing that decides whether something is
        on screen — nobody has to remember to switch an announcement off
        the morning after the event.
        """
        now = now or timezone.now()
        return self.filter(is_active=True, publish_at__lte=now).filter(
            models.Q(expires_at__isnull=True) | models.Q(expires_at__gt=now)
        )

    def for_audience(self, audience):
        return self.filter(audience__in=[audience, NewsItem.Audience.BOTH])


class NewsItem(models.Model):
    class Audience(models.TextChoices):
        GUEST = "GUEST", "Guests"
        STAFF = "STAFF", "Staff"
        BOTH = "BOTH", "Guests and staff"

    class Kind(models.TextChoices):
        NEWS = "NEWS", "News"
        EVENT = "EVENT", "Event"

    title = models.CharField(max_length=150)
    body = models.TextField()
    title_en = models.CharField(max_length=150, blank=True)
    body_en = models.TextField(blank=True)

    kind = models.CharField(max_length=10, choices=Kind.choices, default=Kind.NEWS)
    audience = models.CharField(
        max_length=10,
        choices=Audience.choices,
        default=Audience.GUEST,
        db_index=True,
        help_text="Who this is for. Guest items also appear on the room TV.",
    )
    department = models.ForeignKey(
        "departments.Department",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="news_items",
        help_text=(
            "Staff items only: leave empty for the whole hotel, or pick a "
            "department to show it to that team alone."
        ),
    )

    # When the event itself happens — shown to the reader, and separate
    # from the publish window, which decides when the notice is up.
    event_at = models.DateTimeField(
        null=True, blank=True, help_text="For an event: when it takes place."
    )
    location = models.CharField(max_length=150, blank=True)

    is_pinned = models.BooleanField(
        default=False, help_text="Keep at the top regardless of date."
    )
    is_active = models.BooleanField(default=True)
    publish_at = models.DateTimeField(
        default=timezone.now, help_text="Not shown before this moment."
    )
    expires_at = models.DateTimeField(
        null=True, blank=True, help_text="Empty means it stays up."
    )

    icon = models.CharField(
        max_length=50,
        default="Megaphone",
        help_text="A lucide-react icon name, e.g. Megaphone, Music, Waves, Utensils.",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = NewsItemQuerySet.as_manager()

    class Meta:
        ordering = ["-is_pinned", "-publish_at", "-id"]
        verbose_name = "News item"
        verbose_name_plural = "News and events"

    def __str__(self):
        return self.title

    @property
    def is_published(self) -> bool:
        return NewsItem.objects.published().filter(pk=self.pk).exists()
