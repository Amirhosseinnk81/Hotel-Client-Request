from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.models import User

from .models import Guest
from .serializers import (
    GuestLoginSerializer,
    GuestLoginResponseSerializer,
    GuestProfileSerializer,
)


class GuestLoginView(APIView):
    """
    POST /api/v1/auth/guest/login/

    Guest login using national_id + room_number.
    No password required.
    """

    permission_classes = [AllowAny]

    @extend_schema(
        request=GuestLoginSerializer,
        responses={
            200: OpenApiResponse(
                response=GuestLoginResponseSerializer,
                description="Guest authenticated successfully.",
            ),
        },
        tags=["Authentication"],
        auth=[],
    )
    def post(self, request):
        serializer = GuestLoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        return Response(
            serializer.get_tokens(),
            status=status.HTTP_200_OK,
        )


class GuestProfileView(APIView):
    """
    GET /api/v1/guest/profile/

    Return the authenticated guest's own profile.
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(
        responses={
            200: GuestProfileSerializer,
            403: OpenApiResponse(
                description="User is not a guest or has no guest profile."
            ),
        },
        tags=["Guest"],
    )
    def get(self, request):
        if request.user.role != User.Role.GUEST:
            raise PermissionDenied(
                "This endpoint is for guests only."
            )

        try:
            guest = request.user.guest_profile
        except Guest.DoesNotExist:
            raise PermissionDenied(
                "No guest profile associated with this account."
            )

        serializer = GuestProfileSerializer(guest)

        return Response(serializer.data)