from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase


class HealthCheckTests(APITestCase):
    def setUp(self):
        self.url = reverse("core:health-check")

    def test_health_check_returns_200(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, {"success": True, "status": "ok"})

    def test_health_check_does_not_require_authentication(self):
        # No credentials set on self.client at all — should still succeed.
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_health_check_rejects_post(self):
        response = self.client.post(self.url)

        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
