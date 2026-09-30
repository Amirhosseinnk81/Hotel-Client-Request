"""
Two endpoints, each with one fixed scope — the same shape as the stats
summary, and for the same reason: an endpoint that widens or narrows
depending on who called it is one refactor away from showing a guest the
shift briefing.
"""

from rest_framework import generics

from apps.core.permissions import IsGuest, IsStaffReadAdminWrite

from . import services
from .models import NewsItem
from .serializers import NewsItemSerializer


class GuestNewsListView(generics.ListAPIView):
    """GET /api/v1/guest/news/ — what the hotel is telling its guests."""

    serializer_class = NewsItemSerializer
    permission_classes = [IsGuest]
    pagination_class = None

    def get_queryset(self):
        return services.guest_news()


class OperatorNewsListView(generics.ListAPIView):
    """
    GET /api/v1/operator/news/ — staff announcements, hotel-wide plus my
    own department's.

    IsStaffReadAdminWrite, not IsOperator: an admin is a panel user too
    and a shift briefing is theirs to read. It is also the permission
    that keeps guests out, which IsAdminRole would not — a guest is an
    authenticated user (see apps/extensions).
    """

    serializer_class = NewsItemSerializer
    permission_classes = [IsStaffReadAdminWrite]
    pagination_class = None

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return NewsItem.objects.none()
        return services.staff_news(self.request.user)
