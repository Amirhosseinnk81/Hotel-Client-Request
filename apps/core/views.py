from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView


class HealthCheckView(APIView):
    """
    Simple liveness endpoint — confirms the project boots and DRF routing
    works, independent of the database or any app-specific logic.
    """

    permission_classes = [AllowAny]

    def get(self, request):
        return Response({"success": True, "status": "ok"})
