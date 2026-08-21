from django.urls import path

from .views import (
    CategoryDetailView,
    CategoryListCreateView,
    GuestTicketDetailView,
    GuestTicketListCreateView,
    OperatorTicketDetailView,
    OperatorTicketListView,
    OperatorTicketAssignView,
)

urlpatterns = [
    path(
        "categories/",
        CategoryListCreateView.as_view(),
        name="category-list",
    ),
    path(
        "categories/<int:pk>/",
        CategoryDetailView.as_view(),
        name="category-detail",
    ),
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