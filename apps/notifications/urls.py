from django.urls import path

from .views import OperatorEventStreamView

app_name = "notifications"

urlpatterns = [
    path("operator/events/", OperatorEventStreamView.as_view(), name="operator-events"),
]
