from django.urls import path

from .views import GuestHotelInfoListView, GuestLoginView, GuestProfileView


app_name = "guests"


urlpatterns = [
    path(
        "auth/guest/login/",
        GuestLoginView.as_view(),
        name="guest-login",
    ),
    path(
        "guest/profile/",
        GuestProfileView.as_view(),
        name="guest-profile",
    ),
    path(
        "guest/hotel-info/",
        GuestHotelInfoListView.as_view(),
        name="guest-hotel-info",
    ),
]