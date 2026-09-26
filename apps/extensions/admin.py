from django.contrib import admin, messages
from django.utils import timezone

from .models import Extension


@admin.register(Extension)
class ExtensionAdmin(admin.ModelAdmin):
    """
    Where the hotel manages the phone directory. The panel page is
    read-only on purpose — reference data (rooms, departments,
    categories) is managed here, and this is reference data too.

    Deleting from the list marks rows as deleted rather than removing
    them; "Delete permanently" is the only way to actually lose a row.
    """

    list_display = ("extension", "title", "person_name", "department", "location", "is_active", "is_deleted")
    list_filter = ("is_active", "is_deleted", "department")
    search_fields = ("extension", "title", "person_name", "location", "mobile", "email", "notes")
    list_select_related = ("department",)
    readonly_fields = ("created_at", "updated_at", "deleted_at")
    actions = ["activate", "deactivate", "send_to_trash", "restore", "delete_permanently"]
    list_per_page = 50

    @admin.action(description="Mark as in use")
    def activate(self, request, queryset):
        self.message_user(request, f"{queryset.update(is_active=True)} marked as in use.", messages.SUCCESS)

    @admin.action(description="Mark as out of use")
    def deactivate(self, request, queryset):
        self.message_user(request, f"{queryset.update(is_active=False)} marked as out of use.", messages.SUCCESS)

    @admin.action(description="Move to the trash (restorable)")
    def send_to_trash(self, request, queryset):
        count = queryset.filter(is_deleted=False).update(is_deleted=True, deleted_at=timezone.now())
        self.message_user(request, f"{count} moved to the trash.", messages.SUCCESS)

    @admin.action(description="Restore from the trash")
    def restore(self, request, queryset):
        count = queryset.filter(is_deleted=True).update(is_deleted=False, deleted_at=None)
        self.message_user(request, f"{count} restored.", messages.SUCCESS)

    @admin.action(description="Delete permanently (cannot be undone)")
    def delete_permanently(self, request, queryset):
        count, _ = queryset.delete()
        self.message_user(request, f"{count} deleted for good.", messages.WARNING)
