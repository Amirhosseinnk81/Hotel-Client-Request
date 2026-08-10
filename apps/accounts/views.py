from rest_framework_simplejwt.views import TokenObtainPairView

from .serializers import OperatorTokenObtainPairSerializer


class OperatorLoginView(TokenObtainPairView):
    """POST /api/v1/auth/operator/login/ — username + password login for operators/admins."""

    serializer_class = OperatorTokenObtainPairSerializer
