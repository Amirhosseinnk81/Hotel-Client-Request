import jwt
from django.conf import settings
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from apps.core.jwt_cookies import REFRESH_COOKIE_NAME
from apps.departments.models import Department
from apps.guests.models import Guest
from apps.rooms.models import Room
from apps.tickets.models import Category, Ticket

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

    def test_access_token_carries_is_supervisor_claim(self):
        # A UI hint for the frontend (which controls to show). The backend
        # never trusts it for authorization — see IsSupervisor, and
        # OperatorAccessLevelTests for the stale-claim case.
        def login_and_decode():
            response = self.client.post(
                self.login_url,
                {"username": "operator_login_test", "password": "Test123456!"},
                format="json",
            )
            return jwt.decode(
                response.data["access"],
                settings.SECRET_KEY,
                algorithms=["HS256"],
            )

        self.assertIs(login_and_decode()["is_supervisor"], False)

        self.operator.is_supervisor = True
        self.operator.save(update_fields=["is_supervisor"])

        self.assertIs(login_and_decode()["is_supervisor"], True)

    def test_access_token_carries_department_code_claim(self):
        # UI hint only: decides whether the IT Ops link is shown. IsITStaff
        # re-reads the department from the database on every request.
        def login_and_decode():
            response = self.client.post(
                self.login_url,
                {"username": "operator_login_test", "password": "Test123456!"},
                format="json",
            )
            return jwt.decode(
                response.data["access"],
                settings.SECRET_KEY,
                algorithms=["HS256"],
            )

        self.assertIsNone(login_and_decode()["department_code"])

        self.operator.department = Department.objects.create(name="IT", code="IT")
        self.operator.save(update_fields=["department"])

        self.assertEqual(login_and_decode()["department_code"], "IT")

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
    """
    GET /api/v1/operator/me/status/ — availability is derived from the
    tickets assigned to the operator, never set by hand: busy while any of
    them is still OPEN or IN_PROGRESS, available again once every one is
    RESOLVED or CANCELLED.
    """

    @classmethod
    def setUpTestData(cls):
        cls.department = Department.objects.create(name="Housekeeping", code="HK_AVAIL")
        cls.other_department = Department.objects.create(name="Maintenance", code="MT_AVAIL")
        cls.category = Category.objects.create(name="Towels", code="TOWELS_AVAIL")
        cls.room = Room.objects.create(number="501", status=Room.Status.OCCUPIED)

        cls.guest_user = User.objects.create_user(
            username="availability_guest",
            role=User.Role.GUEST,
        )
        cls.guest = Guest.objects.create(
            user=cls.guest_user,
            full_name="Test Guest",
            national_id="0077777777",
            phone="09127778888",
            room=cls.room,
        )
        cls.operator = User.objects.create_user(
            username="availability_operator",
            password="Test123456!",
            role=User.Role.OPERATOR,
            department=cls.department,
        )
        cls.url = reverse("accounts:operator-availability")

    def assign(self, ticket_status=Ticket.Status.IN_PROGRESS, department=None):
        return Ticket.objects.create(
            guest=self.guest,
            department=department or self.department,
            category=self.category,
            room=self.room,
            title="Extra towels",
            description="Two towels, please.",
            status=ticket_status,
            assigned_to=self.operator,
        )

    def my_status(self):
        self.client.force_authenticate(self.operator)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        return response.data

    def test_operator_with_no_tickets_is_available(self):
        self.assertEqual(self.my_status(), {"is_available": True, "active_tickets": 0})

    def test_an_assigned_ticket_makes_the_operator_busy(self):
        self.assign()

        self.assertEqual(self.my_status(), {"is_available": False, "active_tickets": 1})

    def test_an_assigned_but_not_yet_started_ticket_counts_too(self):
        # A supervisor may assign a ticket that is still OPEN.
        self.assign(Ticket.Status.OPEN)

        self.assertFalse(self.my_status()["is_available"])

    def test_stays_busy_until_every_assigned_ticket_is_closed(self):
        first = self.assign()
        second = self.assign()

        first.status = Ticket.Status.RESOLVED
        first.resolution = "Delivered."
        first.save()
        self.assertEqual(self.my_status(), {"is_available": False, "active_tickets": 1})

        second.status = Ticket.Status.CANCELLED
        second.save()
        self.assertEqual(self.my_status(), {"is_available": True, "active_tickets": 0})

    def test_a_guest_reopen_makes_the_same_operator_busy_again(self):
        # A reopened ticket keeps its assignee, so the operator who handled
        # it is busy again without anyone having to set anything.
        ticket = self.assign(Ticket.Status.RESOLVED)
        ticket.resolution = "Delivered."
        ticket.resolved_at = timezone.now()
        ticket.save()
        self.assertTrue(self.my_status()["is_available"])

        self.client.force_authenticate(self.guest_user)
        reopen = self.client.post(reverse("tickets:guest-ticket-reopen", kwargs={"pk": ticket.pk}))
        self.assertEqual(reopen.status_code, status.HTTP_200_OK)

        self.assertEqual(self.my_status(), {"is_available": False, "active_tickets": 1})

    def test_tickets_in_another_department_do_not_count(self):
        # E.g. an operator moved to a new department with an old ticket
        # still assigned — busy-ness is about their current department.
        self.assign(department=self.other_department)

        self.assertTrue(self.my_status()["is_available"])

    def test_the_manual_toggle_is_gone(self):
        self.client.force_authenticate(self.operator)

        response = self.client.patch(self.url, {"is_available": False}, format="json")

        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_guest_cannot_access_availability_endpoint(self):
        self.client.force_authenticate(self.guest_user)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_unauthenticated_cannot_access_availability_endpoint(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
