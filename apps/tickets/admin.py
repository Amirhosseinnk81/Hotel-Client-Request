from django.contrib import admin

from .models import Category, Ticket, TicketHistory


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "is_active", "created_at")
    list_filter = ("is_active",)
    search_fields = ("name", "code")
    ordering = ("name",)


class TicketHistoryInline(admin.TabularInline):
    model = TicketHistory
    extra = 0
    readonly_fields = ("user", "action", "old_value", "new_value", "created_at")
    can_delete = False


@admin.register(Ticket)
class TicketAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "title",
        "guest",
        "room",
        "department",
        "category",
        "status",
        "priority",
        "assigned_to",
        "created_at",
    )
    list_filter = ("status", "priority", "department", "category")
    search_fields = ("title", "description", "guest__full_name", "guest__national_id")
    ordering = ("-created_at",)
    inlines = [TicketHistoryInline]