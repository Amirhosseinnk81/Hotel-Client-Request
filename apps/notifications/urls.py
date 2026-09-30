from django.urls import path

from .views import GuestEventStreamView, OperatorEventStreamView

app_name = "notifications"

urlpatterns = [
    path("operator/events/", OperatorEventStreamView.as_view(), name="operator-events"),
    path("guest/events/", GuestEventStreamView.as_view(), name="guest-events"),
]
