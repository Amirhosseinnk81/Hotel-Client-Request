from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from .views import OperatorLoginView

app_name = "accounts"

urlpatterns = [
    path("auth/operator/login/", OperatorLoginView.as_view(), name="operator-login"),
    path("auth/token/refresh/", TokenRefreshView.as_view(), name="token-refresh"),
]
