from django.contrib import admin

from .models import Room


@admin.register(Room)
class RoomAdmin(admin.ModelAdmin):
    list_display = ("number", "floor", "status")
    list_filter = ("status", "floor")
    search_fields = ("number",)
    ordering = ("number",)
