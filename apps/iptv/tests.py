"""Stage 3.4 — the in-room television."""

from io import StringIO

from django.core.management import call_command
from django.test import TestCase, override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import User
from apps.departments.models import Department
from apps.guests.models import Guest, HotelInfo
from apps.news.models import NewsItem
from apps.rooms.models import Room
from apps.tickets.models import Category, Ticket

from .auth import signature_for

KEY = "test-iptv-key"


class IptvTestData:
    @classmethod
    def setUpTestData(cls):
        cls.department = Department.objects.create(name="خانه‌داری", code="HK_TV")
        cls.category = Category.objects.create(name="حوله", code="TOWELS_TV", sla_minutes=45)
        cls.room = Room.objects.create(number="305", status=Room.Status.OCCUPIED)
        cls.other_room = Room.objects.create(number="410", status=Room.Status.OCCUPIED)
        cls.guest = cls.make_guest("0011122233", cls.room, "سارا احمدی")
        cls.neighbour = cls.make_guest("0044455566", cls.other_room, "علی رضایی")
        HotelInfo.objects.create(title="صبحانه", body="۷ تا ۱۰ صبح", order=1)
        HotelInfo.objects.create(title="وای‌فای", body="رمز: guest2026", order=2, is_active=False)
        NewsItem.objects.create(
            title="موسیقی زنده در لابی",
            body="امشب از ساعت ۲۱",
            audience=NewsItem.Audience.GUEST,
            kind=NewsItem.Kind.EVENT,
            location="لابی",
        )
        NewsItem.objects.create(
            title="بریفینگ شیفت شب",
            body="ساعت ۲۳ در دفتر",
            audience=NewsItem.Audience.STAFF,
        )

    @classmethod
    def make_guest(cls, national_id, room, name):
        user = User.objects.create(username=f"guest_{national_id}", role=User.Role.GUEST)
        user.set_unusable_password()
        user.save()
        return Guest.objects.create(user=user, full_name=name, national_id=national_id, room=room)

    @classmethod
    def ticket(cls, guest, title, ticket_status=Ticket.Status.OPEN):
        return Ticket.objects.create(
            guest=guest,
            department=cls.department,
            category=cls.category,
            room=guest.room,
            title=title,
            description="…",
            status=ticket_status,
        )


@override_settings(IPTV_SHARED_KEY=KEY, IPTV_ALLOWED_NETWORKS="", IPTV_PAGE_SECRET="")
class IptvApiTests(IptvTestData, APITestCase):
    def url(self, room_number="305"):
        return reverse("iptv:room-screen", args=[room_number])

    def get(self, room_number="305", **headers):
        return self.client.get(self.url(room_number), **headers)

    def test_the_screen_shows_this_room_s_open_requests(self):
        self.ticket(self.guest, "حوله اضافه")
        self.ticket(self.guest, "تعمیر کولر", Ticket.Status.IN_PROGRESS)
        self.ticket(self.guest, "کار تمام‌شده", Ticket.Status.RESOLVED)
        self.ticket(self.neighbour, "درخواست اتاق دیگر")

        response = self.get(HTTP_X_IPTV_KEY=KEY)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["has_active_stay"])
        titles = [item["title"] for item in response.data["requests"]]
        self.assertCountEqual(titles, ["حوله اضافه", "تعمیر کولر"])
        first = response.data["requests"][0]
        self.assertEqual(first["estimated_minutes"], 45)
        self.assertIn(first["status_label"], ("باز", "در حال انجام"))

    def test_the_screen_carries_no_personal_data(self):
        # A television is a screen in a room, not an account: anyone
        # standing in the room sees whatever it shows.
        self.ticket(self.guest, "حوله اضافه")

        body = self.get(HTTP_X_IPTV_KEY=KEY).content.decode()

        for secret in ("0011122233", "سارا احمدی"):
            self.assertNotIn(secret, body)

    def test_only_active_hotel_information_is_shown(self):
        titles = [item["title"] for item in self.get(HTTP_X_IPTV_KEY=KEY).data["hotel_info"]]

        self.assertEqual(titles, ["صبحانه"])

    def test_an_empty_room_and_an_unknown_room_answer_the_same(self):
        # Otherwise the screen tells anyone who reaches it which rooms
        # exist and which are sold.
        Room.objects.filter(pk=self.room.pk).update(status=Room.Status.AVAILABLE)
        self.ticket(self.guest, "حوله اضافه")

        vacant = self.get("305", HTTP_X_IPTV_KEY=KEY)
        unknown = self.get("9999", HTTP_X_IPTV_KEY=KEY)

        self.assertEqual(vacant.status_code, status.HTTP_200_OK)
        self.assertEqual(unknown.status_code, status.HTTP_200_OK)
        for response in (vacant, unknown):
            self.assertFalse(response.data["has_active_stay"])
            self.assertEqual(list(response.data["requests"]), [])
        self.assertEqual(vacant.data["hotel_info"], unknown.data["hotel_info"])

    def test_a_departed_guest_disappears_from_the_television(self):
        self.ticket(self.guest, "حوله اضافه")
        # What the PMS does on check-out (apps/pms/services.py).
        Guest.objects.filter(pk=self.guest.pk).update(room=None)
        Room.objects.filter(pk=self.room.pk).update(status=Room.Status.AVAILABLE)

        response = self.get(HTTP_X_IPTV_KEY=KEY)

        self.assertFalse(response.data["has_active_stay"])
        self.assertEqual(list(response.data["requests"]), [])

    def test_without_the_key_nothing_is_shown(self):
        self.assertEqual(self.get().status_code, status.HTTP_403_FORBIDDEN)

    def test_a_wrong_key_is_refused(self):
        self.assertEqual(self.get(HTTP_X_IPTV_KEY="nope").status_code, status.HTTP_403_FORBIDDEN)

    @override_settings(IPTV_SHARED_KEY="")
    def test_an_unconfigured_integration_is_closed(self):
        self.assertEqual(self.get(HTTP_X_IPTV_KEY=KEY).status_code, status.HTTP_403_FORBIDDEN)

    @override_settings(IPTV_ALLOWED_NETWORKS="10.20.0.0/24")
    def test_the_key_alone_is_not_enough_when_a_network_is_set(self):
        refused = self.get(HTTP_X_IPTV_KEY=KEY, REMOTE_ADDR="192.168.1.5")
        allowed = self.get(HTTP_X_IPTV_KEY=KEY, REMOTE_ADDR="10.20.0.31")

        self.assertEqual(refused.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(allowed.status_code, status.HTTP_200_OK)

    @override_settings(IPTV_ALLOWED_NETWORKS="10.20.0.0/24")
    def test_a_forwarded_for_header_cannot_fake_the_network(self):
        response = self.get(
            HTTP_X_IPTV_KEY=KEY, REMOTE_ADDR="192.168.1.5", HTTP_X_FORWARDED_FOR="10.20.0.31"
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class TvPageTests(IptvTestData, TestCase):
    def url(self, room_number="305"):
        return reverse("tv:room", args=[room_number])

    @override_settings(IPTV_ALLOWED_NETWORKS="", IPTV_PAGE_SECRET="")
    def test_an_unconfigured_page_is_refused_not_served(self):
        self.assertEqual(self.client.get(self.url()).status_code, status.HTTP_403_FORBIDDEN)

    @override_settings(IPTV_ALLOWED_NETWORKS="10.20.0.0/24", IPTV_PAGE_SECRET="")
    def test_the_page_renders_for_a_television_on_the_iptv_network(self):
        self.ticket(self.guest, "حوله اضافه")

        response = self.client.get(self.url(), REMOTE_ADDR="10.20.0.31")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        body = response.content.decode()
        self.assertIn("حوله اضافه", body)
        self.assertIn("صبحانه", body)  # the hotel's information
        self.assertIn("موسیقی زنده در لابی", body)  # guest news (apps/news)
        # A staff briefing is not for a screen in a guest's room.
        self.assertNotIn("بریفینگ شیفت شب", body)
        self.assertIn("۳۰۵", body)  # the room number, in Persian digits
        self.assertNotIn("0011122233", body)

    @override_settings(IPTV_ALLOWED_NETWORKS="10.20.0.0/24", IPTV_PAGE_SECRET="")
    def test_a_television_somewhere_else_gets_nothing(self):
        response = self.client.get(self.url(), REMOTE_ADDR="192.168.1.5")

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    @override_settings(IPTV_ALLOWED_NETWORKS="", IPTV_PAGE_SECRET="s3cret")
    def test_the_signature_stops_one_room_reading_another(self):
        self.ticket(self.neighbour, "درخواست اتاق ۴۱۰")

        wrong = self.client.get(f"{self.url('410')}?t={signature_for('305')}")
        right = self.client.get(f"{self.url('410')}?t={signature_for('410')}")

        self.assertEqual(wrong.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(right.status_code, status.HTTP_200_OK)
        self.assertIn("درخواست اتاق ۴۱۰", right.content.decode())

    @override_settings(IPTV_ALLOWED_NETWORKS="10.20.0.0/24", IPTV_PAGE_SECRET="s3cret")
    def test_when_both_are_configured_both_must_pass(self):
        signed = f"{self.url()}?t={signature_for('305')}"

        self.assertEqual(self.client.get(signed, REMOTE_ADDR="192.168.1.5").status_code, 403)
        self.assertEqual(self.client.get(self.url(), REMOTE_ADDR="10.20.0.31").status_code, 403)
        self.assertEqual(self.client.get(signed, REMOTE_ADDR="10.20.0.31").status_code, 200)

    @override_settings(IPTV_ALLOWED_NETWORKS="10.20.0.0/24", IPTV_PAGE_SECRET="")
    def test_an_empty_room_still_shows_the_hotel_s_information(self):
        # A television in an empty room should greet, not error.
        response = self.client.get(self.url("9999"), REMOTE_ADDR="10.20.0.31")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("خوش آمدید", response.content.decode())


class IptvUrlCommandTests(IptvTestData, TestCase):
    @override_settings(IPTV_PAGE_SECRET="s3cret")
    def test_it_prints_one_signed_url_per_room(self):
        out = StringIO()

        call_command("iptv_urls", "--base-url", "https://hotel.example.com/", stdout=out)

        output = out.getvalue()
        self.assertIn(f"https://hotel.example.com/tv/305/?t={signature_for('305')}", output)
        self.assertIn("410", output)

    @override_settings(IPTV_PAGE_SECRET="")
    def test_it_warns_when_the_urls_carry_no_signature(self):
        out = StringIO()

        call_command("iptv_urls", "--base-url", "https://hotel.example.com", stdout=out)

        self.assertIn("IPTV_PAGE_SECRET is not set", out.getvalue())
