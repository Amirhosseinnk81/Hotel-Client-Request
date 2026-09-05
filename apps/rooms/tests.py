from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import User

from .models import Room, RoomStatusLog


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


class RoomStatusLogTests(APITestCase):
    """Stage 2.7 — the automatic status-change history log."""

    @classmethod
    def setUpTestData(cls):
        cls.admin = User.objects.create_user(
            username="log_admin", password="Test123456!", role=User.Role.ADMIN
        )
        cls.operator = User.objects.create_user(
            username="log_operator", password="Test123456!", role=User.Role.OPERATOR
        )
        cls.room = Room.objects.create(number="201", floor="2")

    def test_creating_a_room_writes_no_log_entry(self):
        # save() ran once (INSERT) with is_new=True — nothing to compare
        # against, so no RoomStatusLog should exist yet.
        self.assertEqual(RoomStatusLog.objects.filter(room=self.room).count(), 0)

    def test_changing_status_writes_a_log_entry(self):
        self.room.status = Room.Status.MAINTENANCE
        self.room.save()

        entry = RoomStatusLog.objects.get(room=self.room)
        self.assertEqual(entry.previous_status, Room.Status.AVAILABLE)
        self.assertEqual(entry.new_status, Room.Status.MAINTENANCE)

    def test_saving_without_a_status_change_writes_no_entry(self):
        self.room.floor = "3"
        self.room.save()

        self.assertEqual(RoomStatusLog.objects.filter(room=self.room).count(), 0)

    def test_multiple_transitions_are_all_logged_in_order(self):
        self.room.status = Room.Status.OCCUPIED
        self.room.save()
        self.room.status = Room.Status.MAINTENANCE
        self.room.save()
        self.room.status = Room.Status.AVAILABLE
        self.room.save()

        entries = list(
            RoomStatusLog.objects.filter(room=self.room).order_by("changed_at")
        )
        self.assertEqual(len(entries), 3)
        self.assertEqual(
            [(e.previous_status, e.new_status) for e in entries],
            [
                (Room.Status.AVAILABLE, Room.Status.OCCUPIED),
                (Room.Status.OCCUPIED, Room.Status.MAINTENANCE),
                (Room.Status.MAINTENANCE, Room.Status.AVAILABLE),
            ],
        )

    def test_api_status_change_is_logged_too(self):
        # Not just direct .save() calls in tests — the same PATCH the
        # frontend/admin actually uses must trigger the log via the
        # serializer -> instance.save() path.
        self.client.force_authenticate(self.admin)
        url = reverse("rooms:room-detail", kwargs={"pk": self.room.pk})

        self.client.patch(url, {"status": Room.Status.MAINTENANCE})

        self.assertTrue(
            RoomStatusLog.objects.filter(
                room=self.room,
                previous_status=Room.Status.AVAILABLE,
                new_status=Room.Status.MAINTENANCE,
            ).exists()
        )

    def test_admin_can_list_status_logs(self):
        self.room.status = Room.Status.MAINTENANCE
        self.room.save()

        self.client.force_authenticate(self.admin)
        url = reverse("rooms:room-status-log-list", kwargs={"pk": self.room.pk})
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["new_status"], Room.Status.MAINTENANCE)

    def test_operator_cannot_list_status_logs(self):
        self.client.force_authenticate(self.operator)
        url = reverse("rooms:room-status-log-list", kwargs={"pk": self.room.pk})
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_anonymous_cannot_list_status_logs(self):
        url = reverse("rooms:room-status-log-list", kwargs={"pk": self.room.pk})
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
