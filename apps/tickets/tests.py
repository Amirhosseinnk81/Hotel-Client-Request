from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from apps.departments.models import Department
from apps.guests.models import Guest
from apps.rooms.models import Room
from .models import Category, Ticket, TicketHistory, TicketNote

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
