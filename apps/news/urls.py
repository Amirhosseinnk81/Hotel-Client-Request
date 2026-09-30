from django.urls import path

from .views import GuestNewsListView, OperatorNewsListView

app_name = "news"

urlpatterns = [
    path("guest/news/", GuestNewsListView.as_view(), name="guest-news"),
    path("operator/news/", OperatorNewsListView.as_view(), name="operator-news"),
]
