from django.urls import path

from .views import CookieTokenRefreshView, LogoutView, OperatorLoginView

app_name = "accounts"

urlpatterns = [
    path("auth/operator/login/", OperatorLoginView.as_view(), name="operator-login"),
    path("auth/token/refresh/", CookieTokenRefreshView.as_view(), name="token-refresh"),
    path("auth/logout/", LogoutView.as_view(), name="logout"),
]
