from django.contrib import admin

from .models import Guest, HotelInfo


@admin.register(Guest)
class GuestAdmin(admin.ModelAdmin):
    list_display = ("full_name", "national_id", "phone", "room")
    search_fields = ("full_name", "national_id", "phone")
    list_filter = ("room",)
    ordering = ("full_name",)


@admin.register(HotelInfo)
class HotelInfoAdmin(admin.ModelAdmin):
    """The guest help page (Wi-Fi, breakfast hours, check-out...)."""

    list_display = ("title", "title_en", "is_active", "order")
    list_editable = ("is_active", "order")
    search_fields = ("title", "body", "title_en", "body_en")
