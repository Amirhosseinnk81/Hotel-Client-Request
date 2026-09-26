from django.urls import path

from .views import PmsWebhookView

app_name = "pms"

urlpatterns = [
    path("pms/events/", PmsWebhookView.as_view(), name="webhook"),
]
