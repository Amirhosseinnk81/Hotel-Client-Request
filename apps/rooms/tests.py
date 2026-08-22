from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import User

from .models import Room


class RoomPermissionTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = User.objects.create_user(
            username="room_admin", password="Test123456!", role=User.Role.ADMIN
        )
        cls.operator = User.objects.create_user(
            username="room_operator", password="Test123456!", role=User.Role.OPERATOR
        )
        cls.room = Room.objects.create(number="101", floor="1")

        cls.list_url = reverse("rooms:room-list")
        cls.detail_url = reverse("rooms:room-detail", kwargs={"pk": cls.room.pk})

    def test_anonymous_cannot_list_rooms(self):
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_operator_can_read_but_not_create(self):
        self.client.force_authenticate(self.operator)

        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        response = self.client.post(self.list_url, {"number": "102", "floor": "1"})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_can_create_room(self):
        self.client.force_authenticate(self.admin)

        response = self.client.post(self.list_url, {"number": "103", "floor": "1"})
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(Room.objects.filter(number="103").exists())

    def test_admin_can_update_room_status(self):
        self.client.force_authenticate(self.admin)

        response = self.client.patch(self.detail_url, {"status": Room.Status.MAINTENANCE})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.room.refresh_from_db()
        self.assertEqual(self.room.status, Room.Status.MAINTENANCE)

    def test_operator_cannot_update_room(self):
        self.client.force_authenticate(self.operator)

        response = self.client.patch(self.detail_url, {"status": Room.Status.MAINTENANCE})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_duplicate_room_number_rejected(self):
        self.client.force_authenticate(self.admin)

        response = self.client.post(self.list_url, {"number": "101", "floor": "2"})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_admin_can_delete_room(self):
        extra_room = Room.objects.create(number="999", floor="9")
        self.client.force_authenticate(self.admin)

        url = reverse("rooms:room-detail", kwargs={"pk": extra_room.pk})
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Room.objects.filter(pk=extra_room.pk).exists())