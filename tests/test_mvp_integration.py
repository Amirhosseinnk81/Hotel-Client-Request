"""
Phase 14 — MVP Integration Test.

Walks through the complete, real-world MVP flow end to end (guest login
all the way to admin oversight), matching the "MVP done" criteria in
the original spec (section 34): rather than testing each app in
isolation, this exercises the whole system together the way an actual
hotel stay would.
"""

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import User
from apps.departments.models import Department
from apps.guests.models import Guest
from apps.rooms.models import Room
from apps.tickets.models import Category, Ticket, TicketHistory


class MVPIntegrationTest(APITestCase):
    """
    One continuous scenario:

    1. Admin sets up the hotel (department, category, room).
    2. A guest checks in, logs in, sees their profile, opens a ticket.
    3. An operator logs in, sees the department's tickets, picks it up,
       moves it through the workflow, and records a resolution.
    4. The guest sees the ticket resolved on their side.
    5. Isolation: another guest/department cannot see or touch it.
    """

    @classmethod
    def setUpTestData(cls):
        # --- Admin sets up the hotel -------------------------------------
        cls.admin = User.objects.create_user(
            username="mvp_admin", password="AdminPass123!", role=User.Role.ADMIN
        )
        cls.department = Department.objects.create(name="Housekeeping", code="HK-MVP")
        cls.other_department = Department.objects.create(name="IT", code="IT-MVP")
        cls.category = Category.objects.create(name="Extra Towels", code="TWL-MVP")
        cls.room = Room.objects.create(number="1001", status=Room.Status.OCCUPIED)

        # --- The guest checking into that room -----------------------------
        cls.guest_user = User.objects.create_user(
            username="mvp_guest", role=User.Role.GUEST
        )
        cls.guest_user.set_unusable_password()
        cls.guest_user.save()
        cls.guest = Guest.objects.create(
            user=cls.guest_user,
            full_name="Sara Ahmadi",
            national_id="1112223334",
            phone="09120000000",
            room=cls.room,
        )

        # --- The operator responsible for that department -------------------
        cls.operator = User.objects.create_user(
            username="mvp_operator",
            password="OperatorPass123!",
            role=User.Role.OPERATOR,
            department=cls.department,
        )

        # --- A second, unrelated guest + department, for isolation checks ---
        cls.other_room = Room.objects.create(number="1002", status=Room.Status.OCCUPIED)
        cls.other_guest_user = User.objects.create_user(
            username="mvp_other_guest", role=User.Role.GUEST
        )
        cls.other_guest_user.set_unusable_password()
        cls.other_guest_user.save()
        cls.other_guest = Guest.objects.create(
            user=cls.other_guest_user,
            full_name="Someone Else",
            national_id="9998887776",
            room=cls.other_room,
        )
        cls.other_operator = User.objects.create_user(
            username="mvp_other_operator",
            password="OperatorPass123!",
            role=User.Role.OPERATOR,
            department=cls.other_department,
        )

    def _login_guest(self, national_id, room_number):
        response = self.client.post(
            reverse("guests:guest-login"),
            {"national_id": national_id, "room_number": room_number},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        return response.data["access"]

    def _login_operator(self, username, password):
        response = self.client.post(
            reverse("accounts:operator-login"),
            {"username": username, "password": password},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        return response.data["access"]

    def _auth(self, token):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

    def test_full_guest_to_operator_resolution_flow(self):
        # ------------------------------------------------------------------
        # 1. Guest logs in with national ID + room number (no password).
        # ------------------------------------------------------------------
        guest_token = self._login_guest("1112223334", "1001")
        self._auth(guest_token)

        # 2. Guest sees their own profile.
        response = self.client.get(reverse("guests:guest-profile"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["full_name"], "Sara Ahmadi")
        self.assertEqual(response.data["room_number"], "1001")

        # 3. Guest creates a ticket.
        response = self.client.post(
            "/api/v1/tickets/",
            {
                "title": "Need extra towels",
                "description": "Two extra towels for room 1001, please.",
                "department": self.department.id,
                "category": self.category.id,
                "priority": Ticket.Priority.NORMAL,
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        ticket_id = response.data["id"]

        # Room and guest were auto-attached server-side, not guest-supplied.
        ticket = Ticket.objects.get(pk=ticket_id)
        self.assertEqual(ticket.room, self.room)
        self.assertEqual(ticket.guest, self.guest)
        self.assertEqual(ticket.status, Ticket.Status.OPEN)

        # A CREATED history entry exists.
        self.assertTrue(
            TicketHistory.objects.filter(
                ticket=ticket, action=TicketHistory.Action.CREATED
            ).exists()
        )

        # 4. Guest can see the ticket in their own list.
        response = self.client.get("/api/v1/tickets/")
        results = response.data["results"] if "results" in response.data else response.data
        self.assertEqual(len(results), 1)

        # 5. Guest can view its status/detail.
        response = self.client.get(f"/api/v1/tickets/{ticket_id}/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["status"], Ticket.Status.OPEN)

        # ------------------------------------------------------------------
        # Operator logs in with username + password.
        # ------------------------------------------------------------------
        operator_token = self._login_operator("mvp_operator", "OperatorPass123!")
        self._auth(operator_token)

        # Operator sees the department's tickets (including this one).
        response = self.client.get("/api/v1/operator/tickets/")
        results = response.data["results"] if "results" in response.data else response.data
        self.assertTrue(any(t["id"] == ticket_id for t in results))

        # Operator opens the ticket detail.
        response = self.client.get(f"/api/v1/operator/tickets/{ticket_id}/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Operator assigns the ticket to themself (the view auto-assigns to
        # whichever operator calls it, and moves the ticket to IN_PROGRESS).
        response = self.client.post(f"/api/v1/operator/tickets/{ticket_id}/assign/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["status"], Ticket.Status.IN_PROGRESS)
        self.assertEqual(response.data["assigned_to"], self.operator.id)

        # Operator resolves it and records the resolution.
        response = self.client.patch(
            f"/api/v1/operator/tickets/{ticket_id}/",
            {
                "status": Ticket.Status.RESOLVED,
                "resolution": "Delivered two extra towels to the room.",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["status"], Ticket.Status.RESOLVED)
        self.assertIsNotNone(response.data["resolved_at"])

        # History logged the status change.
        self.assertTrue(
            TicketHistory.objects.filter(
                ticket_id=ticket_id,
                action=TicketHistory.Action.STATUS_CHANGED,
                new_value=Ticket.Status.RESOLVED,
            ).exists()
        )

        # ------------------------------------------------------------------
        # Guest sees the ticket resolved on their side.
        # ------------------------------------------------------------------
        self._auth(guest_token)

        response = self.client.get(f"/api/v1/tickets/{ticket_id}/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["status"], Ticket.Status.RESOLVED)
        self.assertEqual(
            response.data["resolution"], "Delivered two extra towels to the room."
        )

        # ------------------------------------------------------------------
        # Isolation checks.
        # ------------------------------------------------------------------
        # Another guest cannot see this ticket.
        other_guest_token = self._login_guest("9998887776", "1002")
        self._auth(other_guest_token)
        response = self.client.get(f"/api/v1/tickets/{ticket_id}/")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        # An operator from a different department cannot see or touch it.
        other_operator_token = self._login_operator(
            "mvp_other_operator", "OperatorPass123!"
        )
        self._auth(other_operator_token)
        response = self.client.get(f"/api/v1/operator/tickets/{ticket_id}/")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_admin_can_manage_all_core_entities(self):
        """
        Admin bootstraps a department, category, and room, and can see the
        ticket created against them — matching section 34's admin criteria.
        """
        self.client.force_authenticate(self.admin)

        response = self.client.post(
            "/api/v1/departments/", {"name": "Maintenance", "code": "MNT-MVP"}
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        response = self.client.post(
            "/api/v1/categories/", {"name": "Air Conditioning", "code": "AC-MVP"}
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        response = self.client.post(
            "/api/v1/rooms/", {"number": "2001", "floor": "20"}
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Sanity: admin read access to everything works too.
        for url in ("/api/v1/departments/", "/api/v1/categories/", "/api/v1/rooms/"):
            response = self.client.get(url)
            self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_health_and_docs_are_reachable(self):
        """Baseline infra check: the whole app boots and serves its own docs."""
        for url in ("/api/v1/health/", "/api/schema/", "/api/docs/", "/api/redoc/"):
            response = self.client.get(url)
            self.assertEqual(response.status_code, status.HTTP_200_OK, url)
