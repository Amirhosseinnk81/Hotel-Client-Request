from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from .models import User


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    list_display = (
        "username", "email", "role", "department", "is_supervisor", "is_staff", "is_active",
    )
    list_filter = ("role", "department", "is_supervisor", "is_staff", "is_active")
    search_fields = ("username", "email", "first_name", "last_name")
    ordering = ("username",)

    # is_supervisor is how a hotel admin promotes an operator to their
    # department's supervisor. After the 0004 migration every existing
    # operator is a regular one, so nobody can assign tickets until an
    # admin ticks this for at least one operator per department.
    fieldsets = DjangoUserAdmin.fieldsets + (
        ("Role", {"fields": ("role", "department", "is_supervisor")}),
    )
    add_fieldsets = DjangoUserAdmin.add_fieldsets + (
        ("Role", {"fields": ("role", "department", "is_supervisor")}),
    )