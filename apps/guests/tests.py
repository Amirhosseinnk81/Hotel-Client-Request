from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import User
from apps.core.jwt_cookies import REFRESH_COOKIE_NAME
from apps.rooms.models import Room

from .models import Guest


class GuestAuthenticationTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            username="guest_test",
            password="Test123456!",
            role=User.Role.GUEST,
        )

        cls.room = Room.objects.create(
            number="1205",
            floor="12",
            status=Room.Status.OCCUPIED,
        )

        cls.guest = Guest.objects.create(
            user=cls.user,
            full_name="Test Guest",
            national_id="0012345678",
            phone="09120000000",
            room=cls.room,
        )

        cls.login_url = reverse("guests:guest-login")
        cls.profile_url = reverse("guests:guest-profile")

    def test_guest_login_success(self):
        response = self.client.post(
            self.login_url,
            {
                "national_id": "0012345678",
                "room_number": "1205",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)
        self.assertNotIn("refresh", response.data)
        self.assertIn(REFRESH_COOKIE_NAME, response.cookies)
        self.assertTrue(response.cookies[REFRESH_COOKIE_NAME]["httponly"])
        self.assertEqual(response.data["role"], User.Role.GUEST)

    def test_guest_login_wrong_national_id(self):
        response = self.client.post(
            self.login_url,
            {
                "national_id": "9999999999",
                "room_number": "1205",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_guest_login_wrong_room(self):
        response = self.client.post(
            self.login_url,
            {
                "national_id": "0012345678",
                "room_number": "9999",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_guest_login_available_room(self):
        self.room.status = Room.Status.AVAILABLE
        self.room.save()

        response = self.client.post(
            self.login_url,
            {
                "national_id": "0012345678",
                "room_number": "1205",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_guest_login_maintenance_room(self):
        self.room.status = Room.Status.MAINTENANCE
        self.room.save()

        response = self.client.post(
            self.login_url,
            {
                "national_id": "0012345678",
                "room_number": "1205",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_guest_profile_requires_authentication(self):
        response = self.client.get(self.profile_url)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_guest_profile_success(self):
        login_response = self.client.post(
            self.login_url,
            {
                "national_id": "0012345678",
                "room_number": "1205",
            },
            format="json",
        )

        access_token = login_response.data["access"]

        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {access_token}"
        )

        response = self.client.get(self.profile_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["full_name"], "Test Guest")
        self.assertEqual(response.data["national_id"], "0012345678")
        self.assertEqual(response.data["room_number"], "1205")

    def test_operator_cannot_access_guest_profile(self):
        operator = User.objects.create_user(
            username="operator_test",
            password="Test123456!",
            role=User.Role.OPERATOR,
        )

        login_response = self.client.post(
            reverse("accounts:operator-login"),
            {
                "username": "operator_test",
                "password": "Test123456!",
            },
            format="json",
        )

        access_token = login_response.data["access"]

        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {access_token}"
        )

        response = self.client.get(self.profile_url)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)