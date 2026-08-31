import jwt
from django.conf import settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.core.jwt_cookies import REFRESH_COOKIE_NAME

from .models import User


class UserModelTests(APITestCase):
    def test_str_representation(self):
        user = User.objects.create_user(
            username="model_test",
            password="Test123456!",
            role=User.Role.OPERATOR,
        )

        self.assertEqual(str(user), "model_test (OPERATOR)")


class OperatorLoginTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.operator = User.objects.create_user(
            username="operator_login_test",
            password="Test123456!",
            role=User.Role.OPERATOR,
        )
        cls.admin = User.objects.create_user(
            username="admin_login_test",
            password="Test123456!",
            role=User.Role.ADMIN,
        )
        cls.guest_user = User.objects.create_user(
            username="guest_login_test",
            role=User.Role.GUEST,
        )
        cls.guest_user.set_unusable_password()
        cls.guest_user.save()

        cls.login_url = reverse("accounts:operator-login")
        cls.refresh_url = reverse("accounts:token-refresh")

    def test_operator_can_login(self):
        response = self.client.post(
            self.login_url,
            {"username": "operator_login_test", "password": "Test123456!"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)
        # Refresh token must NOT be in the JSON body — it's httpOnly-cookie
        # only (see apps/core/jwt_cookies.py). A regression here would mean
        # frontend JS can read it again, defeating the whole migration.
        self.assertNotIn("refresh", response.data)
        self.assertIn(REFRESH_COOKIE_NAME, response.cookies)
        cookie = response.cookies[REFRESH_COOKIE_NAME]
        self.assertTrue(cookie["httponly"])
        self.assertEqual(cookie["samesite"], "Lax")
        self.assertEqual(response.data["role"], "OPERATOR")

    def test_admin_can_login_via_operator_endpoint(self):
        response = self.client.post(
            self.login_url,
            {"username": "admin_login_test", "password": "Test123456!"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["role"], "ADMIN")

    def test_wrong_password_rejected(self):
        response = self.client.post(
            self.login_url,
            {"username": "operator_login_test", "password": "wrong-password"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_nonexistent_user_rejected(self):
        response = self.client.post(
            self.login_url,
            {"username": "does_not_exist", "password": "whatever"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_guest_cannot_login_via_operator_endpoint(self):
        response = self.client.post(
            self.login_url,
            {"username": "guest_login_test", "password": "anything"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_access_token_contains_role_claim(self):
        response = self.client.post(
            self.login_url,
            {"username": "operator_login_test", "password": "Test123456!"},
            format="json",
        )

        access_token = response.data["access"]
        decoded = jwt.decode(
            access_token,
            settings.SECRET_KEY,
            algorithms=["HS256"],
        )

        self.assertEqual(decoded["role"], "OPERATOR")

    def test_access_token_contains_username_claim(self):
        response = self.client.post(
            self.login_url,
            {"username": "operator_login_test", "password": "Test123456!"},
            format="json",
        )

        access_token = response.data["access"]
        decoded = jwt.decode(
            access_token,
            settings.SECRET_KEY,
            algorithms=["HS256"],
        )

        self.assertEqual(decoded["username"], "operator_login_test")

    def test_token_refresh_success(self):
        login_response = self.client.post(
            self.login_url,
            {"username": "operator_login_test", "password": "Test123456!"},
            format="json",
        )
        # The test client automatically carries cookies set by a previous
        # response into the next request, same as a browser would.
        self.assertIn(REFRESH_COOKIE_NAME, login_response.cookies)

        response = self.client.post(self.refresh_url, {}, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)
        self.assertNotIn("refresh", response.data)
        # ROTATE_REFRESH_TOKENS=True — a new cookie should be issued too.
        self.assertIn(REFRESH_COOKIE_NAME, response.cookies)

    def test_token_refresh_preserves_username_claim(self):
        self.client.post(
            self.login_url,
            {"username": "operator_login_test", "password": "Test123456!"},
            format="json",
        )

        response = self.client.post(self.refresh_url, {}, format="json")

        decoded = jwt.decode(
            response.data["access"],
            settings.SECRET_KEY,
            algorithms=["HS256"],
        )
        self.assertEqual(decoded["username"], "operator_login_test")

    def test_token_refresh_rejects_missing_cookie(self):
        response = self.client.post(self.refresh_url, {}, format="json")

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_token_refresh_rejects_invalid_cookie(self):
        self.client.cookies[REFRESH_COOKIE_NAME] = "not-a-real-token"

        response = self.client.post(self.refresh_url, {}, format="json")

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_logout_blacklists_refresh_token_and_clears_cookie(self):
        login_response = self.client.post(
            self.login_url,
            {"username": "operator_login_test", "password": "Test123456!"},
            format="json",
        )

        logout_response = self.client.post(reverse("accounts:logout"))
        self.assertEqual(logout_response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(logout_response.cookies[REFRESH_COOKIE_NAME].value, "")

        # The blacklisted refresh token must no longer work.
        self.client.cookies[REFRESH_COOKIE_NAME] = login_response.cookies[
            REFRESH_COOKIE_NAME
        ].value
        refresh_after_logout = self.client.post(self.refresh_url, {}, format="json")
        self.assertEqual(refresh_after_logout.status_code, status.HTTP_401_UNAUTHORIZED)


class OperatorAvailabilityTests(APITestCase):
    """Stage 2.2: an operator toggling their own available/busy status."""

    @classmethod
    def setUpTestData(cls):
        cls.operator = User.objects.create_user(
            username="availability_operator",
            password="Test123456!",
            role=User.Role.OPERATOR,
        )
        cls.other_operator = User.objects.create_user(
            username="availability_colleague",
            password="Test123456!",
            role=User.Role.OPERATOR,
        )
        cls.guest_user = User.objects.create_user(
            username="availability_guest",
            role=User.Role.GUEST,
        )
        cls.url = reverse("accounts:operator-availability")

    def test_is_available_defaults_to_true(self):
        self.assertTrue(self.operator.is_available)

    def test_operator_can_set_self_unavailable(self):
        self.client.force_authenticate(self.operator)

        response = self.client.patch(self.url, {"is_available": False}, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data["is_available"])

        self.operator.refresh_from_db()
        self.assertFalse(self.operator.is_available)

    def test_operator_can_set_self_available_again(self):
        self.operator.is_available = False
        self.operator.save(update_fields=["is_available"])
        self.client.force_authenticate(self.operator)

        response = self.client.patch(self.url, {"is_available": True}, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.operator.refresh_from_db()
        self.assertTrue(self.operator.is_available)

    def test_toggling_own_status_does_not_affect_colleague(self):
        self.client.force_authenticate(self.operator)

        self.client.patch(self.url, {"is_available": False}, format="json")

        self.other_operator.refresh_from_db()
        self.assertTrue(self.other_operator.is_available)

    def test_guest_cannot_access_availability_endpoint(self):
        self.client.force_authenticate(self.guest_user)

        response = self.client.patch(self.url, {"is_available": False}, format="json")

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_unauthenticated_cannot_access_availability_endpoint(self):
        response = self.client.patch(self.url, {"is_available": False}, format="json")

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)