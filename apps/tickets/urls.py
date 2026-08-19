from django.urls import path

from .views import (
    GuestTicketDetailView,
    GuestTicketListCreateView,
)


urlpatterns = [
    path(
        "tickets/",
        GuestTicketListCreateView.as_view(),
        name="guest-ticket-list-create",
    ),
    path(
        "tickets/<int:pk>/",
        GuestTicketDetailView.as_view(),
        name="guest-ticket-detail",
),
]