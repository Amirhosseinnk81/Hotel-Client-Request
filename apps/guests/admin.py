from django.contrib import admin

from .models import Guest


@admin.register(Guest)
class GuestAdmin(admin.ModelAdmin):
    list_display = ("full_name", "national_id", "phone", "room")
    search_fields = ("full_name", "national_id", "phone")
    list_filter = ("room",)
    ordering = ("full_name",)
