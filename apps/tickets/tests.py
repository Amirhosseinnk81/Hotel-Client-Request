import io
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone
from PIL import Image
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from apps.departments.models import Department
from apps.guests.models import Guest
from apps.rooms.models import Room
from .models import (
    Category,
    QuickRequestTemplate,
    Ticket,
    TicketAttachment,
    TicketHistory,
    TicketNote,
)

User = get_user_model()


class GuestTicketAPITests(APITestCase):

    def setUp(self):
        self.room = Room.objects.create(
            number="101",
            status=Room.Status.OCCUPIED,
        )

        self.user = User.objects.create_user(
            username="guest101",
            role=User.Role.GUEST,
        )

        self.guest = Guest.objects.create(
            user=self.user,
            full_name="Test Guest",
            national_id="0012345678",
            phone="09120000000",
            room=self.room,
        )

        self.department = Department.objects.create(
            name="Housekeeping",
            code="HOUSEKEEPING",
        )

        self.category = Category.objects.create(
            name="Towels",
            code="TOWELS",
        )

        self.url = "/api/v1/tickets/"

    def authenticate(self):
        refresh = RefreshToken.for_user(self.user)

        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")

    def test_unauthenticated_guest_cannot_list_tickets(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 401)

    def test_authenticated_guest_can_list_tickets(self):
        self.authenticate()

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)

    def test_guest_can_create_ticket(self):
        self.authenticate()

        data = {
            "title": "Extra Towel",
            "description": "Please send two extra towels.",
            "department": self.department.id,
            "category": self.category.id,
            "priority": Ticket.Priority.NORMAL,
        }

        response = self.client.post(
            self.url,
            data,
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(Ticket.objects.count(), 1)

        ticket = Ticket.objects.first()

        self.assertEqual(ticket.guest, self.guest)
        self.assertEqual(ticket.status, Ticket.Status.OPEN)

    def test_guest_can_only_see_own_tickets(self):
        other_user = User.objects.create_user(
            username="guest102",
            role=User.Role.GUEST,
        )

        other_room = Room.objects.create(
            number="102",
            status=Room.Status.OCCUPIED,
        )

        other_guest = Guest.objects.create(
            user=other_user,
            full_name="Other Guest",
            national_id="0098765432",
            phone="09121111111",
            room=other_room,
        )

        Ticket.objects.create(
            guest=self.guest,
            department=self.department,
            category=self.category,
            room=self.room,
            title="My Ticket",
            description="My request",
        )

        Ticket.objects.create(
            guest=other_guest,
            department=self.department,
            category=self.category,
            room=other_room,
            title="Other Ticket",
            description="Other request",
        )

        self.authenticate()

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(response.data["results"][0]["title"], "My Ticket")

    def test_guest_cannot_change_ticket_status_on_create(self):
        self.authenticate()

        data = {
            "title": "TV Problem",
            "description": "TV is not working.",
            "department": self.department.id,
            "category": self.category.id,
            "priority": Ticket.Priority.HIGH,
            "status": Ticket.Status.RESOLVED,
        }

        response = self.client.post(
            self.url,
            data,
            format="json",
        )

        self.assertEqual(response.status_code, 201)

        ticket = Ticket.objects.get()

        self.assertEqual(
            ticket.status,
            Ticket.Status.OPEN,
        )

    def test_guest_can_retrieve_own_ticket(self):
        ticket = Ticket.objects.create(
            guest=self.guest,
            department=self.department,
            category=self.category,
            room=self.room,
            title="My Ticket",
            description="My request",
        )

        self.authenticate()

        response = self.client.get(f"{self.url}{ticket.id}/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["id"], ticket.id)
        self.assertEqual(response.data["title"], "My Ticket")

    def test_guest_cannot_retrieve_other_guest_ticket(self):
        other_user = User.objects.create_user(
            username="guest102",
            role=User.Role.GUEST,
        )

        other_room = Room.objects.create(
            number="102",
            status=Room.Status.OCCUPIED,
        )

        other_guest = Guest.objects.create(
            user=other_user,
            full_name="Other Guest",
            national_id="0098765432",
            phone="09121111111",
            room=other_room,
        )

        ticket = Ticket.objects.create(
            guest=other_guest,
            department=self.department,
            category=self.category,
            room=other_room,
            title="Other Ticket",
            description="Other request",
        )

        self.authenticate()

        response = self.client.get(f"{self.url}{ticket.id}/")

        self.assertEqual(response.status_code, 404)

    def test_guest_can_update_own_ticket(self):
        ticket = Ticket.objects.create(
            guest=self.guest,
            department=self.department,
            category=self.category,
            room=self.room,
            title="Old Title",
            description="Old description",
        )

        self.authenticate()

        response = self.client.patch(
            f"{self.url}{ticket.id}/",
            {
                "title": "Updated Title",
                "description": "Updated description",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200)

        ticket.refresh_from_db()

        self.assertEqual(ticket.title, "Updated Title")
        self.assertEqual(
            ticket.description,
            "Updated description",
        )

    def test_guest_cannot_change_ticket_status(self):
        ticket = Ticket.objects.create(
            guest=self.guest,
            department=self.department,
            category=self.category,
            room=self.room,
            title="Test Ticket",
            description="Test description",
        )

        self.authenticate()

        response = self.client.patch(
            f"{self.url}{ticket.id}/",
            {
                "status": Ticket.Status.RESOLVED,
            },
            format="json",
        )

        self.assertNotEqual(response.status_code, 200)

        ticket.refresh_from_db()

        self.assertEqual(
            ticket.status,
            Ticket.Status.OPEN,
        )


class OperatorTicketAPITests(APITestCase):

    def setUp(self):
        self.department = Department.objects.create(
            name="Housekeeping",
            code="HOUSEKEEPING",
        )

        self.other_department = Department.objects.create(
            name="Maintenance",
            code="MAINTENANCE",
        )

        self.category = Category.objects.create(
            name="Towels",
            code="TOWELS",
        )

        self.room = Room.objects.create(
            number="101",
            status=Room.Status.OCCUPIED,
        )

        self.guest_user = User.objects.create_user(
            username="guest101",
            role=User.Role.GUEST,
        )

        self.guest = Guest.objects.create(
            user=self.guest_user,
            full_name="Test Guest",
            national_id="0012345678",
            phone="09120000000",
            room=self.room,
        )

        self.operator_user = User.objects.create_user(
            username="operator101",
            password="testpassword",
            role=User.Role.OPERATOR,
            department=self.department,
        )

        self.other_operator_user = User.objects.create_user(
            username="operator102",
            password="testpassword",
            role=User.Role.OPERATOR,
            department=self.other_department,
        )

        self.ticket = Ticket.objects.create(
            guest=self.guest,
            department=self.department,
            category=self.category,
            room=self.room,
            title="Extra Towel",
            description="Please send two extra towels.",
            priority=Ticket.Priority.NORMAL,
        )

        self.other_ticket = Ticket.objects.create(
            guest=self.guest,
            department=self.other_department,
            category=self.category,
            room=self.room,
            title="TV Problem",
            description="TV is not working.",
            priority=Ticket.Priority.HIGH,
        )

        self.list_url = "/api/v1/operator/tickets/"

    def authenticate_operator(self):
        refresh = RefreshToken.for_user(self.operator_user)

        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")

    def test_operator_can_list_department_tickets(self):
        self.authenticate_operator()

        response = self.client.get(self.list_url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(
            response.data["results"][0]["id"],
            self.ticket.id,
        )

    def test_operator_can_retrieve_own_department_ticket(self):
        self.authenticate_operator()

        url = f"{self.list_url}{self.ticket.id}/"

        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["id"], self.ticket.id)

    def test_operator_can_update_ticket_status(self):
        self.authenticate_operator()

        url = f"{self.list_url}{self.ticket.id}/"

        response = self.client.patch(
            url,
            {
                "status": Ticket.Status.IN_PROGRESS,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200)

        self.ticket.refresh_from_db()

        self.assertEqual(
            self.ticket.status,
            Ticket.Status.IN_PROGRESS,
        )

    def test_operator_can_update_ticket_priority(self):
        self.authenticate_operator()

        url = f"{self.list_url}{self.ticket.id}/"

        response = self.client.patch(
            url,
            {
                "priority": Ticket.Priority.URGENT,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200)

        self.ticket.refresh_from_db()

        self.assertEqual(
            self.ticket.priority,
            Ticket.Priority.URGENT,
        )

    def test_operator_cannot_access_other_department_ticket(self):
        self.authenticate_operator()

        url = f"{self.list_url}{self.other_ticket.id}/"

        response = self.client.get(url)

        self.assertEqual(response.status_code, 404)

    def test_operator_cannot_update_other_department_ticket(self):
        self.authenticate_operator()

        url = f"{self.list_url}{self.other_ticket.id}/"

        response = self.client.patch(
            url,
            {
                "status": Ticket.Status.RESOLVED,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 404)

        self.other_ticket.refresh_from_db()

        self.assertEqual(
            self.other_ticket.status,
            Ticket.Status.OPEN,
        )

    def test_guest_cannot_access_operator_ticket_api(self):
        refresh = RefreshToken.for_user(self.guest_user)

        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")

        response = self.client.get(self.list_url)

        self.assertEqual(response.status_code, 403)

    def test_unauthenticated_user_cannot_access_operator_ticket_api(self):
        response = self.client.get(self.list_url)

        self.assertEqual(response.status_code, 401)

    def test_unauthenticated_user_cannot_retrieve_operator_ticket(self):
        url = f"{self.list_url}{self.ticket.id}/"

        response = self.client.get(url)

        self.assertEqual(response.status_code, 401)

    def test_operator_cannot_change_ticket_guest(self):
        self.authenticate_operator()

        url = f"{self.list_url}{self.ticket.id}/"

        response = self.client.patch(
            url,
            {
                "guest": self.guest.id,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200)

        self.ticket.refresh_from_db()

        self.assertEqual(
            self.ticket.guest,
            self.guest,
        )

    def test_operator_cannot_change_ticket_department(self):
        self.authenticate_operator()

        url = f"{self.list_url}{self.ticket.id}/"

        response = self.client.patch(
            url,
            {
                "department": self.other_department.id,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200)

        self.ticket.refresh_from_db()

        self.assertEqual(
            self.ticket.department,
            self.department,
        )

    def test_operator_can_resolve_ticket(self):
        self.authenticate_operator()

        self.ticket.status = Ticket.Status.IN_PROGRESS
        self.ticket.save(update_fields=["status"])

        url = f"{self.list_url}{self.ticket.id}/"

        response = self.client.patch(
            url,
            {
                "status": Ticket.Status.RESOLVED,
                "resolution": "Sent two extra towels to the room.",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200)

        self.ticket.refresh_from_db()

        self.assertEqual(
            self.ticket.status,
            Ticket.Status.RESOLVED,
        )
        self.assertIsNotNone(self.ticket.resolved_at)

    def test_operator_can_assign_ticket_to_self(self):
        self.authenticate_operator()

        url = f"{self.list_url}{self.ticket.id}/assign/"

        response = self.client.post(url)

        self.assertEqual(response.status_code, 200)

        self.ticket.refresh_from_db()

        self.assertEqual(
            self.ticket.assigned_to,
            self.operator_user,
        )

        self.assertEqual(
            self.ticket.status,
            Ticket.Status.IN_PROGRESS,
        )

    def test_self_assign_logs_ticket_history(self):
        """Stage 2.6 bug fix: self-assign must log both ASSIGNED and
        STATUS_CHANGED entries so the Stage 2.1 timeline is accurate."""
        self.authenticate_operator()

        url = f"{self.list_url}{self.ticket.id}/assign/"
        response = self.client.post(url)

        self.assertEqual(response.status_code, 200)

        entries = TicketHistory.objects.filter(ticket=self.ticket).order_by("id")

        assigned_entries = [e for e in entries if e.action == TicketHistory.Action.ASSIGNED]
        self.assertEqual(len(assigned_entries), 1)
        self.assertIsNone(assigned_entries[0].old_value)
        self.assertEqual(assigned_entries[0].new_value, self.operator_user.username)

        status_entries = [
            e for e in entries if e.action == TicketHistory.Action.STATUS_CHANGED
        ]
        self.assertEqual(len(status_entries), 1)
        self.assertEqual(status_entries[0].old_value, Ticket.Status.OPEN)
        self.assertEqual(status_entries[0].new_value, Ticket.Status.IN_PROGRESS)

    def test_reassign_via_patch_logs_ticket_history(self):
        """Stage 2.6 bug fix: reassigning to a colleague through the PATCH
        detail endpoint (not just self-assign) must log an ASSIGNED entry."""
        self.ticket.assigned_to = self.operator_user
        self.ticket.status = Ticket.Status.IN_PROGRESS
        self.ticket.save(update_fields=["assigned_to", "status"])

        other_operator_same_dept = User.objects.create_user(
            username="operator103",
            password="testpassword",
            role=User.Role.OPERATOR,
            department=self.department,
        )

        self.authenticate_operator()
        url = f"{self.list_url}{self.ticket.id}/"

        response = self.client.patch(
            url, {"assigned_to": other_operator_same_dept.id}, format="json"
        )

        self.assertEqual(response.status_code, 200)

        assigned_entries = TicketHistory.objects.filter(
            ticket=self.ticket, action=TicketHistory.Action.ASSIGNED
        )
        self.assertEqual(assigned_entries.count(), 1)
        self.assertEqual(assigned_entries[0].old_value, self.operator_user.username)
        self.assertEqual(assigned_entries[0].new_value, other_operator_same_dept.username)

    def test_updating_unrelated_field_does_not_log_assigned_history(self):
        """No assigned_to in the payload → no spurious ASSIGNED entry."""
        self.authenticate_operator()
        url = f"{self.list_url}{self.ticket.id}/"

        response = self.client.patch(url, {"priority": Ticket.Priority.HIGH}, format="json")

        self.assertEqual(response.status_code, 200)
        self.assertFalse(
            TicketHistory.objects.filter(
                ticket=self.ticket, action=TicketHistory.Action.ASSIGNED
            ).exists()
        )

    def test_operator_cannot_assign_other_department_ticket(self):
        self.authenticate_operator()

        url = f"{self.list_url}{self.other_ticket.id}/assign/"

        response = self.client.post(url)

        self.assertEqual(response.status_code, 404)

        self.other_ticket.refresh_from_db()

        self.assertIsNone(
            self.other_ticket.assigned_to,
        )

        self.assertEqual(
            self.other_ticket.status,
            Ticket.Status.OPEN,
        )

    def test_guest_cannot_assign_ticket(self):
        refresh = RefreshToken.for_user(self.guest_user)

        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")

        url = f"{self.list_url}{self.ticket.id}/assign/"

        response = self.client.post(url)

        self.assertEqual(response.status_code, 403)

        self.ticket.refresh_from_db()

        self.assertIsNone(
            self.ticket.assigned_to,
        )

    def test_unauthenticated_user_cannot_assign_ticket(self):
        url = f"{self.list_url}{self.ticket.id}/assign/"

        response = self.client.post(url)

        self.assertEqual(response.status_code, 401)

        self.ticket.refresh_from_db()

        self.assertIsNone(
            self.ticket.assigned_to,
        )

    def test_operator_can_move_open_ticket_to_in_progress(self):
        self.authenticate_operator()

        url = f"{self.list_url}{self.ticket.id}/"

        response = self.client.patch(
            url,
            {"status": Ticket.Status.IN_PROGRESS},
            format="json",
        )

        self.assertEqual(response.status_code, 200)

        self.ticket.refresh_from_db()

        self.assertEqual(
            self.ticket.status,
            Ticket.Status.IN_PROGRESS,
        )


    def test_operator_can_cancel_open_ticket(self):
        self.authenticate_operator()

        url = f"{self.list_url}{self.ticket.id}/"

        response = self.client.patch(
            url,
            {"status": Ticket.Status.CANCELLED},
            format="json",
        )

        self.assertEqual(response.status_code, 200)

        self.ticket.refresh_from_db()

        self.assertEqual(
            self.ticket.status,
            Ticket.Status.CANCELLED,
        )


    def test_operator_can_reopen_in_progress_ticket(self):
        self.ticket.status = Ticket.Status.IN_PROGRESS
        self.ticket.save(update_fields=["status"])

        self.authenticate_operator()

        url = f"{self.list_url}{self.ticket.id}/"

        response = self.client.patch(
            url,
            {"status": Ticket.Status.OPEN},
            format="json",
        )

        self.assertEqual(response.status_code, 200)

        self.ticket.refresh_from_db()

        self.assertEqual(
            self.ticket.status,
            Ticket.Status.OPEN,
        )


    def test_operator_cannot_resolve_open_ticket_directly(self):
        self.authenticate_operator()

        url = f"{self.list_url}{self.ticket.id}/"

        response = self.client.patch(
            url,
            {"status": Ticket.Status.RESOLVED},
            format="json",
        )

        self.assertEqual(response.status_code, 400)

        self.ticket.refresh_from_db()

        self.assertEqual(
            self.ticket.status,
            Ticket.Status.OPEN,
        )


    def test_operator_cannot_reopen_resolved_ticket(self):
        self.ticket.status = Ticket.Status.RESOLVED
        self.ticket.save(update_fields=["status"])

        self.authenticate_operator()

        url = f"{self.list_url}{self.ticket.id}/"

        response = self.client.patch(
            url,
            {"status": Ticket.Status.OPEN},
            format="json",
        )

        self.assertEqual(response.status_code, 400)

        self.ticket.refresh_from_db()

        self.assertEqual(
            self.ticket.status,
            Ticket.Status.RESOLVED,
        )


    def test_operator_cannot_change_cancelled_ticket_status(self):
        self.ticket.status = Ticket.Status.CANCELLED
        self.ticket.save(update_fields=["status"])

        self.authenticate_operator()

        url = f"{self.list_url}{self.ticket.id}/"

        response = self.client.patch(
            url,
            {"status": Ticket.Status.IN_PROGRESS},
            format="json",
        )

        self.assertEqual(response.status_code, 400)

        self.ticket.refresh_from_db()

        self.assertEqual(
            self.ticket.status,
            Ticket.Status.CANCELLED,
        )

    def test_operator_can_filter_tickets_by_status(self):
        Ticket.objects.create(
            guest=self.guest,
            department=self.department,
            category=self.category,
            room=self.room,
            title="Resolved Ticket",
            description="Resolved request",
            status=Ticket.Status.RESOLVED,
        )

        self.authenticate_operator()

        response = self.client.get(
            self.list_url,
            {"status": Ticket.Status.RESOLVED},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(
            response.data["results"][0]["status"],
            Ticket.Status.RESOLVED,
        )

    def test_operator_can_filter_tickets_by_priority(self):
        Ticket.objects.create(
            guest=self.guest,
            department=self.department,
            category=self.category,
            room=self.room,
            title="Urgent Ticket",
            description="Urgent request",
            priority=Ticket.Priority.URGENT,
        )

        self.authenticate_operator()

        response = self.client.get(
            self.list_url,
            {"priority": Ticket.Priority.URGENT},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(
            response.data["results"][0]["priority"],
            Ticket.Priority.URGENT,
        )

    def test_operator_can_filter_tickets_by_assigned_operator(self):
        self.ticket.assigned_to = self.operator_user
        self.ticket.save(update_fields=["assigned_to"])

        self.authenticate_operator()

        response = self.client.get(
            self.list_url,
            {"assigned_to": self.operator_user.id},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(
            response.data["results"][0]["assigned_to"],
            self.operator_user.id,
        )

    def test_operator_can_search_ticket_by_title(self):
        Ticket.objects.create(
            guest=self.guest,
            department=self.department,
            category=self.category,
            room=self.room,
            title="Air Conditioner Problem",
            description="Room AC is not working.",
        )

        self.authenticate_operator()

        response = self.client.get(
            self.list_url,
            {"search": "Air Conditioner"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(
            response.data["results"][0]["title"],
            "Air Conditioner Problem",
        )

    def test_operator_can_search_ticket_by_description(self):
        Ticket.objects.create(
            guest=self.guest,
            department=self.department,
            category=self.category,
            room=self.room,
            title="Maintenance Request",
            description="The bathroom water heater is broken.",
        )

        self.authenticate_operator()

        response = self.client.get(
            self.list_url,
            {"search": "water heater"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 1)
        self.assertIn(
            "water heater",
            response.data["results"][0]["description"],
        )

    def test_operator_can_order_tickets(self):
        older_ticket = Ticket.objects.create(
            guest=self.guest,
            department=self.department,
            category=self.category,
            room=self.room,
            title="Older Ticket",
            description="Older request",
        )

        newer_ticket = Ticket.objects.create(
            guest=self.guest,
            department=self.department,
            category=self.category,
            room=self.room,
            title="Newer Ticket",
            description="Newer request",
        )

        self.authenticate_operator()

        response = self.client.get(
            self.list_url,
            {"ordering": "created_at"},
        )

        self.assertEqual(response.status_code, 200)

        ids = [
            item["id"]
            for item in response.data["results"]
        ]

        self.assertEqual(
            ids,
            [
                self.ticket.id,
                older_ticket.id,
                newer_ticket.id,
            ],
        )

    def test_operator_ticket_list_is_paginated(self):
        for index in range(12):
            Ticket.objects.create(
                guest=self.guest,
                department=self.department,
            category=self.category,
            room=self.room,
            title=f"Ticket {index}",
                description=f"Request {index}",
            )

        self.authenticate_operator()

        response = self.client.get(self.list_url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 13)
        self.assertIsNotNone(response.data["next"])
        self.assertIsNone(response.data["previous"])
        self.assertEqual(len(response.data["results"]), 10)


    def test_operator_can_access_second_ticket_page(self):
        for index in range(12):
            Ticket.objects.create(
                guest=self.guest,
                department=self.department,
                category=self.category,
                room=self.room,
                title=f"Ticket {index}",
                description=f"Request {index}",
            )

        self.authenticate_operator()

        response = self.client.get(
            self.list_url,
            {"page": 2},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 13)
        self.assertIsNotNone(response.data["previous"])
        self.assertEqual(len(response.data["results"]), 3)


class TicketTimelineAPITests(APITestCase):
    """Stage 2.1: merged history + notes timeline for a ticket."""

    def setUp(self):
        self.department = Department.objects.create(
            name="Housekeeping",
            code="HOUSEKEEPING",
        )

        self.other_department = Department.objects.create(
            name="Maintenance",
            code="MAINTENANCE",
        )

        self.category = Category.objects.create(
            name="Towels",
            code="TOWELS",
        )

        self.room = Room.objects.create(
            number="101",
            status=Room.Status.OCCUPIED,
        )

        self.guest_user = User.objects.create_user(
            username="guest101",
            role=User.Role.GUEST,
        )

        self.guest = Guest.objects.create(
            user=self.guest_user,
            full_name="Test Guest",
            national_id="0012345678",
            phone="09120000000",
            room=self.room,
        )

        self.operator_user = User.objects.create_user(
            username="operator101",
            password="testpassword",
            role=User.Role.OPERATOR,
            department=self.department,
        )

        self.ticket = Ticket.objects.create(
            guest=self.guest,
            department=self.department,
            category=self.category,
            room=self.room,
            title="Extra Towel",
            description="Please send two extra towels.",
            priority=Ticket.Priority.NORMAL,
        )

        self.other_ticket = Ticket.objects.create(
            guest=self.guest,
            department=self.other_department,
            category=self.category,
            room=self.room,
            title="TV Problem",
            description="TV is not working.",
            priority=Ticket.Priority.HIGH,
        )

        self.list_url = "/api/v1/operator/tickets/"
        self.history_url = f"{self.list_url}{self.ticket.id}/history/"
        self.notes_url = f"{self.list_url}{self.ticket.id}/notes/"

    def authenticate_operator(self):
        self.client.force_authenticate(self.operator_user)

    def test_guest_cannot_access_timeline(self):
        self.client.force_authenticate(self.guest_user)

        response = self.client.get(self.history_url)

        self.assertEqual(response.status_code, 403)

    def test_operator_cannot_view_timeline_of_other_department_ticket(self):
        self.authenticate_operator()

        url = f"{self.list_url}{self.other_ticket.id}/history/"
        response = self.client.get(url)

        self.assertEqual(response.status_code, 404)

    def test_operator_can_add_note(self):
        self.authenticate_operator()

        response = self.client.post(
            self.notes_url, {"text": "Guest called again, still waiting."}, format="json"
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["entry_type"], "note")
        self.assertEqual(response.data["author_username"], self.operator_user.username)

        note = TicketNote.objects.get(ticket=self.ticket)
        self.assertEqual(note.text, "Guest called again, still waiting.")
        self.assertEqual(note.author, self.operator_user)

    def test_empty_note_is_rejected(self):
        self.authenticate_operator()

        response = self.client.post(self.notes_url, {"text": "   "}, format="json")

        self.assertEqual(response.status_code, 400)

    def test_operator_cannot_add_note_to_other_department_ticket(self):
        self.authenticate_operator()

        url = f"{self.list_url}{self.other_ticket.id}/notes/"
        response = self.client.post(url, {"text": "Should not work."}, format="json")

        self.assertEqual(response.status_code, 404)

    def test_timeline_merges_history_and_notes_chronologically(self):
        # The ticket already has a CREATED history entry from setUp
        # (created via ORM directly, not the API, so no CREATED entry
        # actually exists here — assign + note are enough to prove merging
        # and ordering work).
        self.authenticate_operator()

        assign_response = self.client.post(f"{self.list_url}{self.ticket.id}/assign/")
        self.assertEqual(assign_response.status_code, 200)

        note_response = self.client.post(
            self.notes_url, {"text": "Checked on the guest, sending towels now."}, format="json"
        )
        self.assertEqual(note_response.status_code, 201)

        response = self.client.get(self.history_url)

        self.assertEqual(response.status_code, 200)
        entry_types = [entry["entry_type"] for entry in response.data]

        # Both an ASSIGNED and a STATUS_CHANGED history entry, plus the note.
        self.assertIn("history", entry_types)
        self.assertIn("note", entry_types)
        self.assertEqual(entry_types.count("note"), 1)

        # Chronological order: created_at must be non-decreasing.
        created_ats = [entry["created_at"] for entry in response.data]
        self.assertEqual(created_ats, sorted(created_ats))

        # The note itself should be the last entry (posted after assign).
        self.assertEqual(response.data[-1]["entry_type"], "note")
        self.assertEqual(
            response.data[-1]["text"], "Checked on the guest, sending towels now."
        )


class OperatorProductivityAPITests(APITestCase):
    """Stage 2.2: colleague availability exposure + new-ticket polling."""

    def setUp(self):
        self.department = Department.objects.create(
            name="Housekeeping",
            code="HOUSEKEEPING",
        )

        self.category = Category.objects.create(
            name="Towels",
            code="TOWELS",
        )

        self.room = Room.objects.create(
            number="101",
            status=Room.Status.OCCUPIED,
        )

        self.guest_user = User.objects.create_user(
            username="guest201",
            role=User.Role.GUEST,
        )

        self.guest = Guest.objects.create(
            user=self.guest_user,
            full_name="Test Guest",
            national_id="0099999999",
            phone="09121111111",
            room=self.room,
        )

        self.operator_user = User.objects.create_user(
            username="operator201",
            password="testpassword",
            role=User.Role.OPERATOR,
            department=self.department,
        )

        self.busy_colleague = User.objects.create_user(
            username="operator202",
            password="testpassword",
            role=User.Role.OPERATOR,
            department=self.department,
            is_available=False,
        )

        self.colleagues_url = "/api/v1/operator/colleagues/"
        self.new_count_url = "/api/v1/operator/tickets/new-count/"

    def authenticate_operator(self):
        self.client.force_authenticate(self.operator_user)

    def test_colleagues_list_exposes_is_available(self):
        self.authenticate_operator()

        response = self.client.get(self.colleagues_url)

        self.assertEqual(response.status_code, 200)
        by_username = {c["username"]: c for c in response.data}
        self.assertTrue(by_username["operator201"]["is_available"])
        self.assertFalse(by_username["operator202"]["is_available"])

    def test_new_count_is_zero_with_no_new_tickets(self):
        self.authenticate_operator()

        since = timezone.now().isoformat()
        response = self.client.get(self.new_count_url, {"since": since})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 0)

    def test_new_count_reflects_tickets_created_after_since(self):
        self.authenticate_operator()
        since = timezone.now()

        Ticket.objects.create(
            guest=self.guest,
            department=self.department,
            category=self.category,
            room=self.room,
            title="Fresh towels please",
            description="Just arrived, no towels in the room.",
        )

        response = self.client.get(
            self.new_count_url, {"since": since.isoformat()}
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 1)

    def test_new_count_ignores_tickets_from_other_departments(self):
        other_department = Department.objects.create(
            name="Maintenance",
            code="MAINTENANCE2",
        )
        since = timezone.now()

        Ticket.objects.create(
            guest=self.guest,
            department=other_department,
            category=self.category,
            room=self.room,
            title="TV broken",
            description="No signal.",
        )

        self.authenticate_operator()
        response = self.client.get(
            self.new_count_url, {"since": since.isoformat()}
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 0)

    def test_new_count_requires_authentication(self):
        response = self.client.get(
            self.new_count_url, {"since": timezone.now().isoformat()}
        )

        self.assertEqual(response.status_code, 401)

class TicketSlaTests(APITestCase):
    """Stage 2.9: sla_minutes-driven overdue detection."""

    def setUp(self):
        self.department = Department.objects.create(
            name="Housekeeping",
            code="HOUSEKEEPING_SLA",
        )

        self.category = Category.objects.create(
            name="Towels",
            code="TOWELS_SLA",
            sla_minutes=15,
        )

        self.room = Room.objects.create(
            number="301",
            status=Room.Status.OCCUPIED,
        )

        guest_user = User.objects.create_user(
            username="guest301",
            role=User.Role.GUEST,
        )
        self.guest = Guest.objects.create(
            user=guest_user,
            full_name="Test Guest",
            national_id="0088888888",
            phone="09122222222",
            room=self.room,
        )

        self.operator_user = User.objects.create_user(
            username="operator301",
            password="testpassword",
            role=User.Role.OPERATOR,
            department=self.department,
        )

    def make_ticket(self, minutes_ago, status=Ticket.Status.OPEN):
        ticket = Ticket.objects.create(
            guest=self.guest,
            department=self.department,
            category=self.category,
            room=self.room,
            title="Need towels",
            description="No towels left.",
            status=status,
        )
        # created_at is auto_now_add — backdate it directly, same approach
        # as the rest of this file uses for time-dependent assertions.
        Ticket.objects.filter(pk=ticket.pk).update(
            created_at=timezone.now() - timedelta(minutes=minutes_ago)
        )
        ticket.refresh_from_db()
        return ticket

    def test_ticket_within_sla_is_not_overdue(self):
        ticket = self.make_ticket(minutes_ago=5)  # sla_minutes=15
        self.assertFalse(ticket.is_overdue)
        self.assertIsNone(ticket.overdue_since)

    def test_ticket_past_sla_is_overdue(self):
        ticket = self.make_ticket(minutes_ago=20)  # sla_minutes=15
        self.assertTrue(ticket.is_overdue)
        self.assertIsNotNone(ticket.overdue_since)

    def test_resolved_ticket_is_never_overdue(self):
        ticket = self.make_ticket(minutes_ago=999, status=Ticket.Status.RESOLVED)
        self.assertFalse(ticket.is_overdue)

    def test_cancelled_ticket_is_never_overdue(self):
        ticket = self.make_ticket(minutes_ago=999, status=Ticket.Status.CANCELLED)
        self.assertFalse(ticket.is_overdue)

    def test_changing_sla_minutes_immediately_changes_overdue_status(self):
        ticket = self.make_ticket(minutes_ago=20)
        self.assertTrue(ticket.is_overdue)  # 20 > 15

        self.category.sla_minutes = 30
        self.category.save(update_fields=["sla_minutes"])
        ticket.refresh_from_db()

        self.assertFalse(ticket.is_overdue)  # 20 <= 30 now

    def test_operator_ticket_list_exposes_is_overdue(self):
        self.make_ticket(minutes_ago=20)
        self.client.force_authenticate(self.operator_user)

        response = self.client.get("/api/v1/operator/tickets/")

        self.assertEqual(response.status_code, 200)
        results = response.data.get("results", response.data)
        self.assertTrue(results[0]["is_overdue"])
        self.assertIsNotNone(results[0]["overdue_since"])

    def test_category_list_exposes_sla_minutes_for_guest(self):
        guest_user = self.guest.user
        self.client.force_authenticate(guest_user)

        response = self.client.get("/api/v1/categories/")

        self.assertEqual(response.status_code, 200)
        results = response.data.get("results", response.data)
        by_code = {c["code"]: c for c in results}
        self.assertEqual(by_code["TOWELS_SLA"]["sla_minutes"], 15)

    def test_overdue_count_counts_only_own_department(self):
        self.make_ticket(minutes_ago=20)  # overdue, own department
        self.make_ticket(minutes_ago=5)  # not overdue, own department

        other_department = Department.objects.create(
            name="Maintenance",
            code="MAINTENANCE_SLA",
        )
        other_ticket = Ticket.objects.create(
            guest=self.guest,
            department=other_department,
            category=self.category,
            room=self.room,
            title="AC broken",
            description="Not cooling.",
        )
        Ticket.objects.filter(pk=other_ticket.pk).update(
            created_at=timezone.now() - timedelta(minutes=999)
        )

        self.client.force_authenticate(self.operator_user)
        response = self.client.get("/api/v1/operator/tickets/overdue-count/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 1)

    def test_overdue_count_requires_authentication(self):
        response = self.client.get("/api/v1/operator/tickets/overdue-count/")

        self.assertEqual(response.status_code, 401)


class TicketGuestExperienceTests(APITestCase):
    """Stage 2.3: guest rating, reopen, and quick-request templates."""

    def setUp(self):
        self.room = Room.objects.create(
            number="401",
            status=Room.Status.OCCUPIED,
        )

        self.user = User.objects.create_user(
            username="guest401",
            role=User.Role.GUEST,
        )

        self.guest = Guest.objects.create(
            user=self.user,
            full_name="Test Guest",
            national_id="0055555555",
            phone="09123334444",
            room=self.room,
        )

        self.department = Department.objects.create(
            name="Housekeeping",
            code="HOUSEKEEPING_GX",
        )

        self.category = Category.objects.create(
            name="Towels",
            code="TOWELS_GX",
        )

        self.other_user = User.objects.create_user(
            username="guest401_other",
            role=User.Role.GUEST,
        )
        other_room = Room.objects.create(number="402", status=Room.Status.OCCUPIED)
        self.other_guest = Guest.objects.create(
            user=self.other_user,
            full_name="Other Guest",
            national_id="0066666666",
            phone="09125556666",
            room=other_room,
        )

    def authenticate(self, user=None):
        refresh = RefreshToken.for_user(user or self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")

    def make_ticket(self, status=Ticket.Status.OPEN, resolved_minutes_ago=None, guest=None):
        ticket = Ticket.objects.create(
            guest=guest or self.guest,
            department=self.department,
            category=self.category,
            room=(guest or self.guest).room,
            title="Need towels",
            description="No towels left.",
            status=status,
            resolution="Delivered fresh towels." if status == Ticket.Status.RESOLVED else None,
        )
        if resolved_minutes_ago is not None:
            Ticket.objects.filter(pk=ticket.pk).update(
                resolved_at=timezone.now() - timedelta(minutes=resolved_minutes_ago)
            )
        ticket.refresh_from_db()
        return ticket

    # --- Rating -----------------------------------------------------

    def test_guest_can_rate_a_resolved_ticket(self):
        ticket = self.make_ticket(status=Ticket.Status.RESOLVED, resolved_minutes_ago=10)
        self.authenticate()

        response = self.client.post(
            f"/api/v1/tickets/{ticket.pk}/rate/",
            {"rating": 5, "feedback": "Great, fast service!"},
        )

        self.assertEqual(response.status_code, 200)
        ticket.refresh_from_db()
        self.assertEqual(ticket.guest_rating, 5)
        self.assertEqual(ticket.guest_feedback, "Great, fast service!")

    def test_cannot_rate_a_non_resolved_ticket(self):
        ticket = self.make_ticket(status=Ticket.Status.OPEN)
        self.authenticate()

        response = self.client.post(f"/api/v1/tickets/{ticket.pk}/rate/", {"rating": 4})

        self.assertEqual(response.status_code, 400)

    def test_cannot_rate_a_ticket_twice(self):
        ticket = self.make_ticket(status=Ticket.Status.RESOLVED, resolved_minutes_ago=10)
        ticket.guest_rating = 3
        ticket.save(update_fields=["guest_rating"])
        self.authenticate()

        response = self.client.post(f"/api/v1/tickets/{ticket.pk}/rate/", {"rating": 5})

        self.assertEqual(response.status_code, 400)
        ticket.refresh_from_db()
        self.assertEqual(ticket.guest_rating, 3)  # unchanged

    def test_rating_out_of_range_is_rejected(self):
        ticket = self.make_ticket(status=Ticket.Status.RESOLVED, resolved_minutes_ago=10)
        self.authenticate()

        response = self.client.post(f"/api/v1/tickets/{ticket.pk}/rate/", {"rating": 6})

        self.assertEqual(response.status_code, 400)

    def test_guest_cannot_rate_someone_elses_ticket(self):
        ticket = self.make_ticket(
            status=Ticket.Status.RESOLVED,
            resolved_minutes_ago=10,
            guest=self.other_guest,
        )
        self.authenticate()  # authenticated as self.user, not the ticket's owner

        response = self.client.post(f"/api/v1/tickets/{ticket.pk}/rate/", {"rating": 5})

        self.assertEqual(response.status_code, 404)

    # --- Reopen -------------------------------------------------------

    def test_guest_can_reopen_within_window(self):
        ticket = self.make_ticket(status=Ticket.Status.RESOLVED, resolved_minutes_ago=60)
        self.authenticate()

        response = self.client.post(f"/api/v1/tickets/{ticket.pk}/reopen/")

        self.assertEqual(response.status_code, 200)
        ticket.refresh_from_db()
        self.assertEqual(ticket.status, Ticket.Status.OPEN)
        self.assertIsNotNone(ticket.reopened_at)
        self.assertTrue(
            ticket.history.filter(
                action=TicketHistory.Action.STATUS_CHANGED,
                new_value=Ticket.Status.OPEN,
            ).exists()
        )

    def test_cannot_reopen_past_48_hours(self):
        ticket = self.make_ticket(
            status=Ticket.Status.RESOLVED,
            resolved_minutes_ago=48 * 60 + 1,
        )
        self.authenticate()

        response = self.client.post(f"/api/v1/tickets/{ticket.pk}/reopen/")

        self.assertEqual(response.status_code, 400)
        ticket.refresh_from_db()
        self.assertEqual(ticket.status, Ticket.Status.RESOLVED)

    def test_cannot_reopen_twice(self):
        ticket = self.make_ticket(status=Ticket.Status.RESOLVED, resolved_minutes_ago=10)
        self.authenticate()
        first = self.client.post(f"/api/v1/tickets/{ticket.pk}/reopen/")
        self.assertEqual(first.status_code, 200)

        # Resolve it again, then try to reopen a second time.
        ticket.refresh_from_db()
        ticket.status = Ticket.Status.RESOLVED
        ticket.resolved_at = timezone.now()
        ticket.save(update_fields=["status", "resolved_at"])

        second = self.client.post(f"/api/v1/tickets/{ticket.pk}/reopen/")
        self.assertEqual(second.status_code, 400)

    def test_cannot_reopen_a_non_resolved_ticket(self):
        ticket = self.make_ticket(status=Ticket.Status.OPEN)
        self.authenticate()

        response = self.client.post(f"/api/v1/tickets/{ticket.pk}/reopen/")

        self.assertEqual(response.status_code, 400)

    def test_ticket_detail_exposes_can_reopen(self):
        ticket = self.make_ticket(status=Ticket.Status.RESOLVED, resolved_minutes_ago=10)
        self.authenticate()

        response = self.client.get(f"/api/v1/tickets/{ticket.pk}/")

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["can_reopen"])

    # --- Quick request templates ---------------------------------------

    def test_guest_can_list_active_quick_templates_in_order(self):
        QuickRequestTemplate.objects.create(
            title="Towels",
            icon="Droplet",
            department=self.department,
            category=self.category,
            order=2,
        )
        QuickRequestTemplate.objects.create(
            title="Extra pillow",
            icon="Bed",
            department=self.department,
            category=self.category,
            order=1,
        )
        QuickRequestTemplate.objects.create(
            title="Retired template",
            icon="Bell",
            department=self.department,
            category=self.category,
            is_active=False,
        )
        self.authenticate()

        response = self.client.get("/api/v1/quick-templates/")

        self.assertEqual(response.status_code, 200)
        titles = [item["title"] for item in response.data]
        self.assertEqual(titles, ["Extra pillow", "Towels"])

    def test_quick_templates_require_authentication(self):
        response = self.client.get("/api/v1/quick-templates/")

        self.assertEqual(response.status_code, 401)


def _make_test_image(name="photo.png", size_kb=None):
    """A tiny but genuinely valid PNG, so Pillow-backed ImageField
    validation accepts it. If size_kb is given, generates a larger image
    filled with random noise (a solid color compresses to almost nothing
    in PNG regardless of dimensions, which defeats the point of a
    max-size test) so the encoded file actually reaches roughly that size.
    """
    if not size_kb:
        buffer = io.BytesIO()
        Image.new("RGB", (10, 10), color=(255, 0, 0)).save(buffer, format="PNG")
        buffer.seek(0)
        return SimpleUploadedFile(name, buffer.read(), content_type="image/png")

    import math
    import os

    # Random noise barely compresses, so raw size ~= encoded size. Aim a
    # bit above the target so PNG/zlib overhead doesn't undershoot it.
    dimension = max(10, int(math.sqrt((size_kb * 1024 * 1.3) / 3)))
    raw = os.urandom(dimension * dimension * 3)
    image = Image.frombytes("RGB", (dimension, dimension), raw)

    buffer = io.BytesIO()
    image.save(buffer, format="PNG", compress_level=0)
    buffer.seek(0)
    return SimpleUploadedFile(name, buffer.read(), content_type="image/png")


class TicketAttachmentAPITests(APITestCase):
    """Stage 2.8: guest/operator image attachments on a ticket."""

    def setUp(self):
        self.department = Department.objects.create(
            name="Housekeeping",
            code="HOUSEKEEPING_ATT",
        )
        self.other_department = Department.objects.create(
            name="Maintenance",
            code="MAINTENANCE_ATT",
        )

        self.category = Category.objects.create(
            name="Towels",
            code="TOWELS_ATT",
        )

        self.room = Room.objects.create(number="501", status=Room.Status.OCCUPIED)

        self.guest_user = User.objects.create_user(
            username="guest501",
            role=User.Role.GUEST,
        )
        self.guest = Guest.objects.create(
            user=self.guest_user,
            full_name="Attachment Test Guest",
            national_id="0077778888",
            phone="09121112222",
            room=self.room,
        )

        self.other_guest_user = User.objects.create_user(
            username="guest502",
            role=User.Role.GUEST,
        )
        other_room = Room.objects.create(number="502", status=Room.Status.OCCUPIED)
        self.other_guest = Guest.objects.create(
            user=self.other_guest_user,
            full_name="Other Guest",
            national_id="0099990000",
            phone="09123332222",
            room=other_room,
        )

        self.operator_user = User.objects.create_user(
            username="attachment_operator",
            password="testpassword",
            role=User.Role.OPERATOR,
            department=self.department,
        )
        self.other_operator_user = User.objects.create_user(
            username="attachment_operator_2",
            password="testpassword",
            role=User.Role.OPERATOR,
            department=self.department,
        )

        self.ticket = Ticket.objects.create(
            guest=self.guest,
            department=self.department,
            category=self.category,
            room=self.room,
            title="Extra towels",
            description="Please send towels.",
        )

        self.guest_attachments_url = f"/api/v1/tickets/{self.ticket.id}/attachments/"
        self.operator_attachments_url = (
            f"/api/v1/operator/tickets/{self.ticket.id}/attachments/"
        )

    def authenticate_guest(self, user=None):
        refresh = RefreshToken.for_user(user or self.guest_user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")

    def authenticate_operator(self, user=None):
        self.client.force_authenticate(user or self.operator_user)

    # --- Guest upload -----------------------------------------------------

    def test_guest_can_attach_image_to_own_ticket(self):
        self.authenticate_guest()

        response = self.client.post(
            self.guest_attachments_url,
            {"image": _make_test_image()},
            format="multipart",
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(TicketAttachment.objects.filter(ticket=self.ticket).count(), 1)
        attachment = TicketAttachment.objects.get(ticket=self.ticket)
        self.assertEqual(attachment.uploaded_by, self.guest_user)

    def test_guest_cannot_attach_to_someone_elses_ticket(self):
        self.authenticate_guest(self.other_guest_user)

        response = self.client.post(
            self.guest_attachments_url,
            {"image": _make_test_image()},
            format="multipart",
        )

        self.assertEqual(response.status_code, 404)
        self.assertEqual(TicketAttachment.objects.filter(ticket=self.ticket).count(), 0)

    def test_guest_can_attach_regardless_of_status(self):
        self.ticket.status = Ticket.Status.RESOLVED
        self.ticket.save(update_fields=["status"])
        self.authenticate_guest()

        response = self.client.post(
            self.guest_attachments_url,
            {"image": _make_test_image()},
            format="multipart",
        )

        self.assertEqual(response.status_code, 201)

    def test_non_image_file_is_rejected(self):
        self.authenticate_guest()
        fake_file = SimpleUploadedFile(
            "not_an_image.txt", b"just some text", content_type="text/plain"
        )

        response = self.client.post(
            self.guest_attachments_url, {"image": fake_file}, format="multipart"
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(TicketAttachment.objects.filter(ticket=self.ticket).count(), 0)

    def test_oversized_image_is_rejected(self):
        from django.test import override_settings

        self.authenticate_guest()

        with override_settings(MAX_ATTACHMENT_SIZE_MB=1):
            # ~1200x1200 RGB PNG comfortably exceeds 1MB uncompressed-ish.
            big_image = _make_test_image(size_kb=1200)
            response = self.client.post(
                self.guest_attachments_url, {"image": big_image}, format="multipart"
            )

        self.assertEqual(response.status_code, 400)

    # --- Operator upload ----------------------------------------------------

    def test_assigned_operator_can_attach_image(self):
        self.ticket.assigned_to = self.operator_user
        self.ticket.save(update_fields=["assigned_to"])
        self.authenticate_operator()

        response = self.client.post(
            self.operator_attachments_url,
            {"image": _make_test_image()},
            format="multipart",
        )

        self.assertEqual(response.status_code, 201)
        attachment = TicketAttachment.objects.get(ticket=self.ticket)
        self.assertEqual(attachment.uploaded_by, self.operator_user)

    def test_unassigned_operator_in_same_department_cannot_attach(self):
        """Being in the same department isn't enough — must be the
        assignee, per the Stage 2.8 spec (stricter than notes/history)."""
        self.ticket.assigned_to = self.other_operator_user
        self.ticket.save(update_fields=["assigned_to"])
        self.authenticate_operator(self.operator_user)

        response = self.client.post(
            self.operator_attachments_url,
            {"image": _make_test_image()},
            format="multipart",
        )

        self.assertEqual(response.status_code, 404)

    def test_unassigned_ticket_rejects_operator_attachment(self):
        # assigned_to is still None — no one is "the assignee" yet.
        self.authenticate_operator()

        response = self.client.post(
            self.operator_attachments_url,
            {"image": _make_test_image()},
            format="multipart",
        )

        self.assertEqual(response.status_code, 404)

    def test_guest_cannot_use_operator_attachment_endpoint(self):
        self.ticket.assigned_to = self.operator_user
        self.ticket.save(update_fields=["assigned_to"])
        self.authenticate_guest()

        response = self.client.post(
            self.operator_attachments_url,
            {"image": _make_test_image()},
            format="multipart",
        )

        self.assertEqual(response.status_code, 403)

    # --- Read-side exposure ----------------------------------------------

    def test_attachments_appear_on_guest_ticket_detail(self):
        TicketAttachment.objects.create(
            ticket=self.ticket, image=_make_test_image(), uploaded_by=self.guest_user
        )
        self.authenticate_guest()

        response = self.client.get(f"/api/v1/tickets/{self.ticket.id}/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["attachments"]), 1)
        self.assertEqual(
            response.data["attachments"][0]["uploaded_by_username"], "guest501"
        )

    def test_attachments_appear_on_operator_ticket_detail(self):
        TicketAttachment.objects.create(
            ticket=self.ticket, image=_make_test_image(), uploaded_by=self.guest_user
        )
        self.authenticate_operator()

        response = self.client.get(f"/api/v1/operator/tickets/{self.ticket.id}/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["attachments"]), 1)

class AdminStatsSummaryAPITests(APITestCase):
    """Stage 2.4: GET /api/v1/admin/stats/summary/"""

    def setUp(self):
        self.dept_a = Department.objects.create(name="Housekeeping", code="HK_STATS")
        self.dept_b = Department.objects.create(name="Maintenance", code="MAINT_STATS")

        self.category = Category.objects.create(
            name="Towels", code="TOWELS_STATS", sla_minutes=15
        )

        self.room = Room.objects.create(number="401", status=Room.Status.OCCUPIED)

        guest_user = User.objects.create_user(username="guest401", role=User.Role.GUEST)
        self.guest = Guest.objects.create(
            user=guest_user,
            full_name="Test Guest",
            national_id="0099999999",
            phone="09123334444",
            room=self.room,
        )

        self.admin_user = User.objects.create_user(
            username="hotel_admin_stats", password="testpassword", role=User.Role.ADMIN
        )
        self.operator_user = User.objects.create_user(
            username="operator401",
            password="testpassword",
            role=User.Role.OPERATOR,
            department=self.dept_a,
        )

        self.url = "/api/v1/admin/stats/summary/"

    def make_ticket(self, department, status, created_minutes_ago=0, resolved_minutes_ago=None):
        ticket = Ticket.objects.create(
            guest=self.guest,
            department=department,
            category=self.category,
            room=self.room,
            title="Test ticket",
            description="...",
            status=status,
        )
        update_fields = {
            "created_at": timezone.now() - timedelta(minutes=created_minutes_ago)
        }
        if resolved_minutes_ago is not None:
            update_fields["resolved_at"] = timezone.now() - timedelta(
                minutes=resolved_minutes_ago
            )
        Ticket.objects.filter(pk=ticket.pk).update(**update_fields)
        ticket.refresh_from_db()
        return ticket

    def test_unauthenticated_cannot_access(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 401)

    def test_guest_cannot_access(self):
        self.client.force_authenticate(self.guest.user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 403)

    def test_operator_cannot_access(self):
        # Deliberately IsAdminOnly, not IsAdminRole: unlike
        # Category/Department/Room, this endpoint must stay closed to
        # operators even for GET, since it aggregates every department.
        self.client.force_authenticate(self.operator_user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 403)

    def test_admin_can_access_and_sees_status_breakdown(self):
        self.make_ticket(self.dept_a, Ticket.Status.OPEN)
        self.make_ticket(self.dept_a, Ticket.Status.IN_PROGRESS)
        self.make_ticket(self.dept_b, Ticket.Status.RESOLVED, resolved_minutes_ago=10)
        self.make_ticket(self.dept_b, Ticket.Status.CANCELLED)

        self.client.force_authenticate(self.admin_user)
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.data["by_status"],
            {"OPEN": 1, "IN_PROGRESS": 1, "RESOLVED": 1, "CANCELLED": 1},
        )

    def test_by_department_breakdown(self):
        self.make_ticket(self.dept_a, Ticket.Status.OPEN)
        self.make_ticket(self.dept_a, Ticket.Status.OPEN)
        self.make_ticket(self.dept_b, Ticket.Status.RESOLVED, resolved_minutes_ago=5)

        self.client.force_authenticate(self.admin_user)
        response = self.client.get(self.url)

        by_dept = {row["department_name"]: row for row in response.data["by_department"]}
        self.assertEqual(by_dept["Housekeeping"]["open"], 2)
        self.assertEqual(by_dept["Housekeeping"]["total"], 2)
        self.assertEqual(by_dept["Maintenance"]["resolved"], 1)
        self.assertEqual(by_dept["Maintenance"]["total"], 1)

    def test_avg_resolution_minutes_only_counts_last_30_days(self):
        # Resolved 10 minutes ago, created 40 minutes ago -> 30 min resolution.
        self.make_ticket(
            self.dept_a,
            Ticket.Status.RESOLVED,
            created_minutes_ago=40,
            resolved_minutes_ago=10,
        )
        # Resolved 40 days ago -> outside the 30-day window, must be excluded.
        old_ticket = self.make_ticket(
            self.dept_a,
            Ticket.Status.RESOLVED,
            created_minutes_ago=40,
            resolved_minutes_ago=10,
        )
        Ticket.objects.filter(pk=old_ticket.pk).update(
            resolved_at=timezone.now() - timedelta(days=40)
        )

        self.client.force_authenticate(self.admin_user)
        response = self.client.get(self.url)

        self.assertEqual(response.data["avg_resolution_minutes"], 30.0)

    def test_avg_resolution_minutes_is_null_with_no_recent_resolutions(self):
        self.client.force_authenticate(self.admin_user)
        response = self.client.get(self.url)
        self.assertIsNone(response.data["avg_resolution_minutes"])

    def test_overdue_count_is_system_wide(self):
        # sla_minutes=15 on self.category; 20 minutes ago is overdue.
        self.make_ticket(self.dept_a, Ticket.Status.OPEN, created_minutes_ago=20)
        self.make_ticket(self.dept_b, Ticket.Status.IN_PROGRESS, created_minutes_ago=20)
        # Within SLA, not overdue.
        self.make_ticket(self.dept_a, Ticket.Status.OPEN, created_minutes_ago=5)
        # Resolved tickets are never overdue no matter how old.
        self.make_ticket(
            self.dept_b, Ticket.Status.RESOLVED, created_minutes_ago=999, resolved_minutes_ago=1
        )

        self.client.force_authenticate(self.admin_user)
        response = self.client.get(self.url)

        self.assertEqual(response.data["overdue_count"], 2)

    def test_superuser_can_access(self):
        superuser = User.objects.create_superuser(
            username="superuser_stats", password="testpassword", email="s@example.com"
        )
        self.client.force_authenticate(superuser)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
