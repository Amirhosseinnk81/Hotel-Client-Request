from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import serializers
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView


class HealthCheckResponseSerializer(serializers.Serializer):
    success = serializers.BooleanField()
    status = serializers.CharField()


class HealthCheckView(APIView):
    """
    Simple liveness endpoint — confirms the project boots and DRF routing
    works, independent of the database or any app-specific logic.
    """

    permission_classes = [AllowAny]

    @extend_schema(
        tags=["System"],
        auth=[],
        responses={
            200: {
                "type": "object",
                "properties": {
                    "success": {"type": "boolean"},
                    "status": {"type": "string"},
                },
                "required": ["success", "status"],
            }
        },
    )
    def get(self, request):
        return Response({
            "success": True,
            "status": "ok",
        })