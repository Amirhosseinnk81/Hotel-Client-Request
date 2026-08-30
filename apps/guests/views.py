from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.jwt_cookies import set_refresh_cookie
from apps.core.permissions import IsGuest
from apps.core.throttling import GuestLoginRateThrottle

from .models import Guest
from .serializers import (
    GuestLoginSerializer,
    GuestLoginResponseSerializer,
    GuestProfileSerializer,
)


class GuestLoginView(APIView):
    """
    POST /api/v1/auth/guest/login/

    Guest login using national_id + room_number. No password required.

    The refresh token is set as an httpOnly cookie rather than returned in
    the response body — see apps/core/jwt_cookies.py.
    """

    permission_classes = [AllowAny]
    throttle_classes = [GuestLoginRateThrottle]

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
        tokens = serializer.get_tokens()

        response = Response(
            {"access": tokens["access"], "role": tokens["role"]},
            status=status.HTTP_200_OK,
        )
        set_refresh_cookie(response, tokens["refresh"])
        return response


class GuestProfileView(APIView):
    """
    GET /api/v1/guest/profile/

    Return the authenticated guest's own profile.
    """

    permission_classes = [IsGuest]

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
        try:
            guest = request.user.guest_profile
        except Guest.DoesNotExist:
            raise PermissionDenied(
                "No guest profile associated with this account."
            )

        serializer = GuestProfileSerializer(guest)

        return Response(serializer.data)