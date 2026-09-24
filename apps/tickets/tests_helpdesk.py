"""
Helpdesk features inspired by Odoo: editable per-status SMS templates,
the guest ratings report, canned responses, merging duplicate tickets,
and the guest help page (hotel info).
"""

from datetime import timedelta

from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import User
from apps.departments.models import Department
from apps.guests.models import Guest, HotelInfo
from apps.notifications.models import MessageTemplate, SmsMessage
from apps.notifications.services import queue_ticket_sms
from apps.rooms.models import Room

from .models import CannedResponse, Category, Ticket, TicketAttachment, TicketHistory, TicketNote
from .services import compute_admin_stats_summary, compute_department_stats_summary


class HelpdeskTestData:
    @classmethod
    def setUpTestData(cls):
        cls.department = Department.objects.create(name="Housekeeping", code="HK_HD")
        cls.other_department = Department.objects.create(name="Maintenance", code="MT_HD")
        cls.category = Category.objects.create(name="Towels", code="TOWELS_HD")
        cls.room = Room.objects.create(number="H1", status=Room.Status.OCCUPIED)
        cls.guest_user = User.objects.create_user(username="hd_guest", role=User.Role.GUEST)
        cls.guest = Guest.objects.create(
            user=cls.guest_user, full_name="Sara", national_id="0077766655", phone="09120000000", room=cls.room
        )
        other_user = User.objects.create_user(username="hd_guest2", role=User.Role.GUEST)
        cls.other_guest = Guest.objects.create(
            user=other_user, full_name="Ali", national_id="0077766656", room=cls.room
        )
        cls.supervisor = User.objects.create_user(
            username="hd_sup", role=User.Role.OPERATOR, department=cls.department, is_supervisor=True
        )
        cls.operator = User.objects.create_user(
            username="hd_op", role=User.Role.OPERATOR, department=cls.department
        )

    def ticket(self, **kwargs):
        defaults = {
            "guest": self.guest,
            "department": self.department,
            "category": self.category,
            "room": self.room,
            "title": "Towels",
            "description": "Two, please.",
        }
        defaults.update(kwargs)
        return Ticket.objects.create(**defaults)


# -- 1. editable SMS templates --------------------------------------------------------


class MessageTemplateTests(HelpdeskTestData, TestCase):
    def test_the_admin_edited_text_is_what_the_guest_gets(self):
        MessageTemplate.objects.update_or_create(
            event=SmsMessage.Event.TICKET_CREATED,
            defaults={"body": "Request #{ticket_id} ({title}) for room {room} — {department}.", "is_active": True},
        )
        ticket = self.ticket(title="Iron")

        sms = queue_ticket_sms(ticket, SmsMessage.Event.TICKET_CREATED)

        self.assertEqual(sms.body, f"Request #{ticket.pk} (Iron) for room H1 — Housekeeping.")

    def test_a_switched_off_event_sends_nothing(self):
        MessageTemplate.objects.update_or_create(
            event=SmsMessage.Event.TICKET_CANCELLED, defaults={"body": "x", "is_active": False}
        )

        self.assertIsNone(queue_ticket_sms(self.ticket(), SmsMessage.Event.TICKET_CANCELLED))

    def test_defaults_are_seeded_for_every_event(self):
        self.assertEqual(
            set(MessageTemplate.objects.values_list("event", flat=True)),
            set(SmsMessage.Event.values),
        )

    def test_an_unknown_placeholder_is_refused(self):
        template = MessageTemplate(event=SmsMessage.Event.TICKET_CREATED, body="Hi {titel}")

        with self.assertRaises(ValidationError):
            template.clean()


# -- 2. ratings report ------------------------------------------------------------------


class RatingsReportTests(HelpdeskTestData, TestCase):
    def rated(self, stars, feedback="", operator=None, department=None, days_ago=1):
        return self.ticket(
            status=Ticket.Status.RESOLVED,
            resolution="Done",
            resolved_at=timezone.now() - timedelta(days=days_ago),
            guest_rating=stars,
            guest_feedback=feedback,
            assigned_to=operator,
            department=department or self.department,
        )

    def test_department_report(self):
        self.rated(5, "Very quick!", operator=self.operator)
        self.rated(3, operator=self.operator)
        self.rated(4, operator=self.supervisor)
        self.rated(1, days_ago=60)  # outside the 30-day window

        stats = compute_department_stats_summary(self.department)

        self.assertEqual(stats["rating_avg"], 4.0)
        self.assertEqual(stats["rating_count"], 3)
        self.assertEqual(stats["rating_distribution"], {"1": 0, "2": 0, "3": 1, "4": 1, "5": 1})
        self.assertEqual([f["feedback"] for f in stats["recent_feedback"]], ["Very quick!"])
        by_operator = {row["username"]: row for row in stats["by_operator"]}
        self.assertEqual(by_operator["hd_op"]["rating_avg"], 4.0)
        self.assertEqual(by_operator["hd_op"]["rating_count"], 2)
        self.assertEqual(by_operator["hd_sup"]["rating_avg"], 4.0)

    def test_hotel_report_per_department(self):
        self.rated(5)
        self.rated(2, department=self.other_department)

        stats = compute_admin_stats_summary()

        by_department = {row["department_name"]: row for row in stats["by_department"]}
        self.assertEqual(by_department["Housekeeping"]["rating_avg"], 5.0)
        self.assertEqual(by_department["Maintenance"]["rating_avg"], 2.0)
        self.assertEqual(stats["rating_count"], 2)

    def test_no_ratings_means_no_average_rather_than_zero(self):
        stats = compute_department_stats_summary(self.department)

        self.assertIsNone(stats["rating_avg"])
        self.assertEqual(stats["rating_count"], 0)


# -- 3. canned responses and merging duplicates ---------------------------------------


class CannedResponseTests(HelpdeskTestData, APITestCase):
    def test_own_department_and_hotel_wide_ones_only(self):
        CannedResponse.objects.create(title="Mine", body="…", department=self.department)
        CannedResponse.objects.create(title="Everyone", body="…")
        CannedResponse.objects.create(title="Theirs", body="…", department=self.other_department)
        CannedResponse.objects.create(title="Retired", body="…", is_active=False)
        self.client.force_authenticate(self.operator)

        response = self.client.get(reverse("tickets:operator-canned-responses"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(sorted(r["title"] for r in response.data), ["Everyone", "Mine"])

    def test_guests_cannot_read_them(self):
        self.client.force_authenticate(self.guest_user)

        self.assertEqual(
            self.client.get(reverse("tickets:operator-canned-responses")).status_code,
            status.HTTP_403_FORBIDDEN,
        )


class MergeTests(HelpdeskTestData, APITestCase):
    def merge(self, source, target, user=None):
        self.client.force_authenticate(user or self.supervisor)
        return self.client.post(
            reverse("tickets:operator-ticket-merge", kwargs={"pk": source.pk}),
            {"into": target.pk},
            format="json",
        )

    def test_candidates_are_the_same_guests_open_tickets_in_the_department(self):
        first = self.ticket()
        second = self.ticket()
        self.ticket(status=Ticket.Status.RESOLVED, resolution="Done")
        self.ticket(guest=self.other_guest)
        self.ticket(department=self.other_department)
        self.client.force_authenticate(self.operator)

        response = self.client.get(
            reverse("tickets:operator-ticket-merge-candidates", kwargs={"pk": second.pk})
        )

        self.assertEqual([t["id"] for t in response.data], [first.pk])

    def test_merging_folds_the_duplicate_into_the_other_ticket(self):
        target = self.ticket(status=Ticket.Status.IN_PROGRESS, assigned_to=self.operator)
        duplicate = self.ticket(description="Also a bath mat.")
        TicketAttachment.objects.create(ticket=duplicate, image="tickets/photo.jpg")

        response = self.merge(duplicate, target)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        duplicate.refresh_from_db()
        self.assertEqual(duplicate.status, Ticket.Status.CANCELLED)
        self.assertEqual(duplicate.merged_into, target)
        self.assertEqual(target.attachments.count(), 1)
        self.assertIn("Also a bath mat.", TicketNote.objects.get(ticket=target).text)
        self.assertEqual(
            TicketHistory.objects.filter(action=TicketHistory.Action.MERGED).count(), 2
        )
        # The guest's request is still being handled — no "cancelled" SMS.
        self.assertFalse(SmsMessage.objects.filter(event=SmsMessage.Event.TICKET_CANCELLED).exists())

    def test_only_the_supervisor_can_merge(self):
        response = self.merge(self.ticket(), self.ticket(), user=self.operator)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_refused_merges(self):
        target = self.ticket()
        cases = {
            "different guest": self.ticket(guest=self.other_guest),
            "already started": self.ticket(status=Ticket.Status.IN_PROGRESS),
            "itself": target,
        }
        for label, source in cases.items():
            with self.subTest(label):
                self.assertEqual(self.merge(source, target).status_code, status.HTTP_400_BAD_REQUEST)

        closed = self.ticket(status=Ticket.Status.RESOLVED, resolution="Done")
        self.assertEqual(self.merge(self.ticket(), closed).status_code, status.HTTP_400_BAD_REQUEST)

    def test_another_departments_ticket_is_not_found(self):
        theirs = self.ticket(department=self.other_department)

        self.assertEqual(self.merge(self.ticket(), theirs).status_code, status.HTTP_404_NOT_FOUND)

    def test_the_guest_sees_where_the_duplicate_went(self):
        target = self.ticket()
        duplicate = self.ticket()
        self.merge(duplicate, target)
        self.client.force_authenticate(self.guest_user)

        data = self.client.get(reverse("tickets:guest-ticket-detail", kwargs={"pk": duplicate.pk})).data

        self.assertEqual(data["merged_into"], target.pk)


# -- 4. guest help page -------------------------------------------------------------------


class HotelInfoTests(HelpdeskTestData, APITestCase):
    url = reverse("guests:guest-hotel-info")

    def test_guests_get_the_active_entries_in_order(self):
        HotelInfo.objects.create(title="Breakfast", body="7-10", order=2)
        HotelInfo.objects.create(title="Wi-Fi", body="pw", title_en="Wi-Fi", body_en="pw", order=1)
        HotelInfo.objects.create(title="Old", body="…", is_active=False)
        self.client.force_authenticate(self.guest_user)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual([i["title"] for i in response.data], ["Wi-Fi", "Breakfast"])
        self.assertIn("body_en", response.data[0])

    def test_not_public(self):
        # The Wi-Fi password is for guests, not the whole internet.
        self.assertEqual(self.client.get(self.url).status_code, status.HTTP_401_UNAUTHORIZED)
