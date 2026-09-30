from rest_framework import serializers

from .models import NewsItem


class NewsItemSerializer(serializers.ModelSerializer):
    """
    Read-only on the API — news is written in Django Admin, exactly like
    rooms, departments and hotel info.
    """

    department_name = serializers.CharField(
        source="department.name", read_only=True, default=""
    )

    class Meta:
        model = NewsItem
        fields = [
            "id",
            "title",
            "body",
            "title_en",
            "body_en",
            "kind",
            "audience",
            "department",
            "department_name",
            "event_at",
            "location",
            "is_pinned",
            "publish_at",
            "expires_at",
            "icon",
        ]
        read_only_fields = fields
