from django.urls import path

from .views import (
    GuestTicketDetailView,
    GuestTicketListCreateView,
    OperatorTicketDetailView,
    OperatorTicketListView,
    OperatorTicketAssignView,
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
    path(
        "operator/tickets/",
        OperatorTicketListView.as_view(),
        name="operator-ticket-list",
    ),
    path(
        "operator/tickets/<int:pk>/",
        OperatorTicketDetailView.as_view(),
        name="operator-ticket-detail",
    ),
    path(
        "operator/tickets/<int:pk>/assign/",
        OperatorTicketAssignView.as_view(),
        name="operator-ticket-assign",
    ),
]