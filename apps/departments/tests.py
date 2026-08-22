from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import User

from .models import Department


class DepartmentPermissionTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = User.objects.create_user(
            username="dept_admin", password="Test123456!", role=User.Role.ADMIN
        )
        cls.operator = User.objects.create_user(
            username="dept_operator", password="Test123456!", role=User.Role.OPERATOR
        )
        cls.department = Department.objects.create(name="Housekeeping", code="HK")

        cls.list_url = reverse("departments:department-list")
        cls.detail_url = reverse(
            "departments:department-detail", kwargs={"pk": cls.department.pk}
        )

    def test_anonymous_cannot_list_departments(self):
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_operator_can_read_but_not_create(self):
        self.client.force_authenticate(self.operator)

        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]) if "results" in response.data else len(response.data), 1)

        response = self.client.post(self.list_url, {"name": "IT", "code": "IT"})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_can_create_department(self):
        self.client.force_authenticate(self.admin)

        response = self.client.post(self.list_url, {"name": "Maintenance", "code": "MNT"})
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(Department.objects.filter(code="MNT").exists())

    def test_admin_can_update_department(self):
        self.client.force_authenticate(self.admin)

        response = self.client.patch(self.detail_url, {"is_active": False})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.department.refresh_from_db()
        self.assertFalse(self.department.is_active)

    def test_operator_cannot_update_department(self):
        self.client.force_authenticate(self.operator)

        response = self.client.patch(self.detail_url, {"is_active": False})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_duplicate_code_rejected(self):
        self.client.force_authenticate(self.admin)

        response = self.client.post(
            self.list_url, {"name": "Housekeeping 2", "code": "HK"}
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
