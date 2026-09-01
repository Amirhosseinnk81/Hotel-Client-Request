from django.contrib import admin

from .models import (
    Category,
    QuickRequestTemplate,
    Ticket,
    TicketAttachment,
    TicketHistory,
    TicketNote,
)


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "sla_minutes", "is_active", "created_at")
    list_display_links = ("name",)
    # Editable straight from the list — sla_minutes is meant to be tuned
    # per category as an ongoing operational knob (Stage 2.9), not a
    # one-time setup value buried in the detail form.
    list_editable = ("sla_minutes", "is_active")
    list_filter = ("is_active",)
    search_fields = ("name", "code")
    ordering = ("name",)


class TicketHistoryInline(admin.TabularInline):
    model = TicketHistory
    extra = 0
    readonly_fields = ("user", "action", "old_value", "new_value", "created_at")
    can_delete = False


class TicketNoteInline(admin.TabularInline):
    model = TicketNote
    extra = 0
    readonly_fields = ("author", "text", "created_at")
    can_delete = False


class TicketAttachmentInline(admin.TabularInline):
    model = TicketAttachment
    extra = 0
    readonly_fields = ("image", "uploaded_by", "created_at")
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
    inlines = [TicketHistoryInline, TicketNoteInline, TicketAttachmentInline]

    # These fields are governed by business rules that only live in
    # OperatorTicketSerializer (allowed status transitions via
    # Ticket.can_transition_to(), a mandatory resolution before marking a
    # ticket RESOLVED, and auto-populating resolved_at). Django's default
    # ModelAdmin form bypasses all of that, so editing them here directly
    # could leave a ticket in a state the API — and the frontend built
    # against it — never expects (e.g. RESOLVED with no resolution text,
    # or OPEN jumping straight to RESOLVED). Keeping them read-only forces
    # every real workflow change through the API, where those rules are
    # enforced; Admin is still fully useful for oversight and for editing
    # the non-workflow fields (title, description, priority, department,
    # category). guest_rating/guest_feedback/reopened_at are the same
    # story from the guest side — reopened_at in particular is what
    # enforces the one-reopen-ever rule (Stage 2.3), so it must not be
    # editable here either.
    readonly_fields = (
        "status",
        "resolution",
        "resolved_at",
        "assigned_to",
        "guest_rating",
        "guest_feedback",
        "reopened_at",
    )


@admin.register(QuickRequestTemplate)
class QuickRequestTemplateAdmin(admin.ModelAdmin):
    list_display = ("title", "icon", "department", "category", "order", "is_active")
    list_display_links = ("title",)
    list_editable = ("order", "is_active")
    list_filter = ("department", "is_active")
    search_fields = ("title",)
    ordering = ("order", "title")