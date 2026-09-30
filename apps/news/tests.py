"""
Tests for hotel news and events.

Two things are pinned hardest: the publish window (an announcement is on
screen because of its dates, never because somebody remembered to switch
it off) and the audience split (a staff briefing must never reach a
guest's phone or a room television).
"""

from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from apps.departments.models import Department
from apps.guests.models import Guest
from apps.rooms.models import Room

from . import services
from .models import NewsItem

User = get_user_model()


def make_item(title="خبر", **kwargs):
    kwargs.setdefault("body", "متن خبر")
    return NewsItem.objects.create(title=title, **kwargs)


class PublishWindowTests(TestCase):
    def test_something_not_yet_started_is_not_shown(self):
        make_item(publish_at=timezone.now() + timedelta(hours=1))
        self.assertEqual(list(services.guest_news()), [])

    def test_something_finished_is_not_shown(self):
        make_item(
            publish_at=timezone.now() - timedelta(days=2),
            expires_at=timezone.now() - timedelta(hours=1),
        )
        self.assertEqual(list(services.guest_news()), [])

    def test_no_end_date_means_it_stays_up(self):
        item = make_item(publish_at=timezone.now() - timedelta(days=30))
        self.assertEqual(list(services.guest_news()), [item])

    def test_switching_it_off_takes_it_down_without_touching_the_dates(self):
        make_item(is_active=False)
        self.assertEqual(list(services.guest_news()), [])

    def test_pinned_items_come_first_however_old(self):
        newer = make_item("تازه", publish_at=timezone.now() - timedelta(minutes=1))
        pinned = make_item(
            "سنجاق‌شده", publish_at=timezone.now() - timedelta(days=10), is_pinned=True
        )
        self.assertEqual(list(services.guest_news()), [pinned, newer])


class AudienceTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.housekeeping = Department.objects.create(name="خانه‌داری", code="HK")
        cls.room_service = Department.objects.create(name="روم سرویس", code="RS")
        cls.operator = User.objects.create_user(
            username="op", password="x", role="OPERATOR", department=cls.housekeeping
        )
        cls.admin = User.objects.create_user(username="boss", password="x", role="ADMIN")

    def test_a_guest_item_is_not_in_the_staff_list(self):
        make_item("موسیقی زنده", audience=NewsItem.Audience.GUEST)
        self.assertEqual(list(services.staff_news(self.operator)), [])

    def test_a_staff_item_is_not_in_the_guest_list(self):
        make_item("بریفینگ شیفت", audience=NewsItem.Audience.STAFF)
        self.assertEqual(list(services.guest_news()), [])

    def test_both_reaches_everybody(self):
        item = make_item("بسته‌شدن استخر", audience=NewsItem.Audience.BOTH)
        self.assertEqual(list(services.guest_news()), [item])
        self.assertEqual(list(services.staff_news(self.operator)), [item])

    def test_a_department_item_stays_inside_that_department(self):
        mine = make_item(
            "فقط خانه‌داری",
            audience=NewsItem.Audience.STAFF,
            department=self.housekeeping,
        )
        theirs = make_item(
            "فقط روم سرویس",
            audience=NewsItem.Audience.STAFF,
            department=self.room_service,
        )
        visible = list(services.staff_news(self.operator))
        self.assertIn(mine, visible)
        self.assertNotIn(theirs, visible)

    def test_an_item_with_no_department_goes_to_the_whole_hotel(self):
        item = make_item("برای همه", audience=NewsItem.Audience.STAFF)
        self.assertIn(item, services.staff_news(self.operator))
        self.assertIn(item, services.staff_news(self.admin))

    def test_an_admin_has_no_department_and_still_sees_hotel_wide_items(self):
        hotel_wide = make_item("برای همه", audience=NewsItem.Audience.STAFF)
        departmental = make_item(
            "فقط خانه‌داری",
            audience=NewsItem.Audience.STAFF,
            department=self.housekeeping,
        )
        visible = list(services.staff_news(self.admin))
        self.assertEqual(visible, [hotel_wide])
        self.assertNotIn(departmental, visible)


class NewsAPITests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.department = Department.objects.create(name="خانه‌داری", code="HK")
        room = Room.objects.create(number="701", status=Room.Status.OCCUPIED)
        guest_user = User.objects.create_user(username="g1", password="x", role="GUEST")
        cls.guest = Guest.objects.create(
            user=guest_user, full_name="مهمان", national_id="1212121212", room=room
        )
        cls.operator = User.objects.create_user(
            username="op", password="x", role="OPERATOR", department=cls.department
        )
        cls.admin = User.objects.create_user(username="boss", password="x", role="ADMIN")

        cls.guest_item = make_item("موسیقی زنده", audience=NewsItem.Audience.GUEST)
        cls.staff_item = make_item("بریفینگ", audience=NewsItem.Audience.STAFF)

    def test_the_guest_endpoint_shows_guest_items_only(self):
        self.client.force_authenticate(self.guest.user)
        response = self.client.get(reverse("news:guest-news"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual([row["id"] for row in response.data], [self.guest_item.pk])

    def test_a_guest_cannot_read_the_staff_announcements(self):
        self.client.force_authenticate(self.guest.user)
        response = self.client.get(reverse("news:operator-news"))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_an_operator_cannot_use_the_guest_endpoint(self):
        self.client.force_authenticate(self.operator)
        response = self.client.get(reverse("news:guest-news"))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_the_operator_endpoint_shows_staff_items_only(self):
        self.client.force_authenticate(self.operator)
        response = self.client.get(reverse("news:operator-news"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual([row["id"] for row in response.data], [self.staff_item.pk])

    def test_an_admin_reads_the_staff_announcements_too(self):
        self.client.force_authenticate(self.admin)
        response = self.client.get(reverse("news:operator-news"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_the_api_is_read_only(self):
        self.client.force_authenticate(self.admin)
        response = self.client.post(
            reverse("news:operator-news"), {"title": "دستی", "body": "..."}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_an_anonymous_caller_is_refused(self):
        for name in ("news:guest-news", "news:operator-news"):
            with self.subTest(name=name):
                self.assertEqual(
                    self.client.get(reverse(name)).status_code,
                    status.HTTP_401_UNAUTHORIZED,
                )
