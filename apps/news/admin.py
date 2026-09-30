from django.contrib import admin
from django.utils import timezone

from .models import NewsItem


@admin.register(NewsItem)
class NewsItemAdmin(admin.ModelAdmin):
    """
    Where news is actually written — the API is read-only, like rooms,
    departments, hotel info and the extension list.
    """

    list_display = (
        "title",
        "kind",
        "audience",
        "department",
        "event_at",
        "publish_at",
        "expires_at",
        "is_pinned",
        "is_active",
        "live",
    )
    list_filter = ("audience", "kind", "is_active", "is_pinned", "department")
    search_fields = ("title", "body", "title_en", "body_en", "location")
    date_hierarchy = "publish_at"
    fieldsets = (
        (None, {"fields": ("title", "body", "kind", "icon")}),
        (
            "English (optional — falls back to the Persian text)",
            {"fields": ("title_en", "body_en"), "classes": ("collapse",)},
        ),
        ("Who sees it", {"fields": ("audience", "department")}),
        ("Event details", {"fields": ("event_at", "location")}),
        ("When it is up", {"fields": ("publish_at", "expires_at", "is_pinned", "is_active")}),
    )
    actions = ("pin", "unpin", "expire_now")

    @admin.display(boolean=True, description="On screen now")
    def live(self, obj):
        return obj.is_published

    @admin.action(description="Pin to the top")
    def pin(self, request, queryset):
        queryset.update(is_pinned=True)

    @admin.action(description="Unpin")
    def unpin(self, request, queryset):
        queryset.update(is_pinned=False)

    @admin.action(description="Take down now")
    def expire_now(self, request, queryset):
        """
        Sets the end of the window rather than deleting: the announcement
        stays on record, and the window is the only thing that decides
        what is on screen.
        """
        queryset.update(expires_at=timezone.now())
