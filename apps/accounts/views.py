from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from rest_framework_simplejwt.serializers import TokenRefreshSerializer
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView

from apps.core.jwt_cookies import (
    REFRESH_COOKIE_NAME,
    clear_refresh_cookie,
    set_refresh_cookie,
)

from .serializers import OperatorTokenObtainPairSerializer


class OperatorLoginView(TokenObtainPairView):
    """
    POST /api/v1/auth/operator/login/ — username + password login for
    operators/admins.

    The refresh token is set as an httpOnly cookie rather than returned in
    the response body — see apps/core/jwt_cookies.py.
    """

    serializer_class = OperatorTokenObtainPairSerializer

    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)

        if response.status_code == status.HTTP_200_OK:
            refresh = response.data.pop("refresh", None)
            if refresh:
                set_refresh_cookie(response, refresh)

        return response


class CookieTokenRefreshView(APIView):
    """
    POST /api/v1/auth/token/refresh/

    Reads the refresh token from the httpOnly cookie (never from the
    request body) and returns a fresh access token. Because
    ROTATE_REFRESH_TOKENS=True, the old refresh token is blacklisted and a
    new one is written back to the cookie.
    """

    permission_classes = [AllowAny]

    @extend_schema(
        request=None,
        responses={
            200: OpenApiResponse(description="New access token issued."),
            401: OpenApiResponse(description="Missing, invalid, or expired refresh cookie."),
        },
        tags=["Authentication"],
        auth=[],
    )
    def post(self, request):
        refresh_token = request.COOKIES.get(REFRESH_COOKIE_NAME)
        if not refresh_token:
            return Response(
                {"success": False, "message": "Refresh token cookie is missing."},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        serializer = TokenRefreshSerializer(data={"refresh": refresh_token})
        try:
            serializer.is_valid(raise_exception=True)
        except TokenError as exc:
            raise InvalidToken(exc.args[0]) from exc

        response = Response({"access": serializer.validated_data["access"]})

        new_refresh = serializer.validated_data.get("refresh")
        if new_refresh:
            set_refresh_cookie(response, new_refresh)

        return response


class LogoutView(APIView):
    """
    POST /api/v1/auth/logout/

    Blacklists the current refresh token (so a copy of the cookie can't be
    replayed after logout) and clears the cookie. Works for both guest and
    operator sessions — logout isn't role-specific.
    """

    permission_classes = [AllowAny]

    @extend_schema(
        request=None,
        responses={204: OpenApiResponse(description="Logged out.")},
        tags=["Authentication"],
        auth=[],
    )
    def post(self, request):
        refresh_token = request.COOKIES.get(REFRESH_COOKIE_NAME)

        if refresh_token:
            try:
                RefreshToken(refresh_token).blacklist()
            except TokenError:
                # Already invalid/expired/blacklisted — fine, we're clearing
                # the cookie either way and logout should never fail loudly
                # just because the token was already dead.
                pass

        response = Response(status=status.HTTP_204_NO_CONTENT)
        clear_refresh_cookie(response)
        return response
