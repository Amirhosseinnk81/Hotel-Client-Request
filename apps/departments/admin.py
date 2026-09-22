from django.contrib import admin

from .models import Department


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "is_active", "auto_assign", "created_at")
    # Auto-assignment is an operational switch a manager flips per
    # department, so it's editable straight from the list.
    list_editable = ("auto_assign",)
    list_filter = ("is_active", "auto_assign")
    search_fields = ("name", "code")
    ordering = ("name",)
