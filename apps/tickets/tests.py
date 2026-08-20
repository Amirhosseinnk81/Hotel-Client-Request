from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from apps.departments.models import Department
from apps.guests.models import Guest
from apps.rooms.models import Room
from .models import Ticket


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

        self.url = "/api/v1/tickets/"

    def authenticate(self):
        refresh = RefreshToken.for_user(self.user)

        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}"
        )

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
            title="My Ticket",
            description="My request",
        )

        Ticket.objects.create(
            guest=other_guest,
            department=self.department,
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
            title="My Ticket",
            description="My request",
        )

        self.authenticate()

        response = self.client.get(
            f"{self.url}{ticket.id}/"
        )

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
            title="Other Ticket",
            description="Other request",
        )

        self.authenticate()

        response = self.client.get(
            f"{self.url}{ticket.id}/"
        )

        self.assertEqual(response.status_code, 404)

    def test_guest_can_update_own_ticket(self):
        ticket = Ticket.objects.create(
            guest=self.guest,
            department=self.department,
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
            title="Extra Towel",
            description="Please send two extra towels.",
            priority=Ticket.Priority.NORMAL,
        )

        self.other_ticket = Ticket.objects.create(
            guest=self.guest,
            department=self.other_department,
            title="TV Problem",
            description="TV is not working.",
            priority=Ticket.Priority.HIGH,
        )

        self.list_url = "/api/v1/operator/tickets/"

    def authenticate_operator(self):
        refresh = RefreshToken.for_user(self.operator_user)

        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}"
        )

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

        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}"
        )

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

        url = f"{self.list_url}{self.ticket.id}/"

        response = self.client.patch(
            url,
            {
                "status": Ticket.Status.RESOLVED,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200)

        self.ticket.refresh_from_db()

        self.assertEqual(
            self.ticket.status,
            Ticket.Status.RESOLVED,
        )