"""
Auto-assignment by workload and the two-stage SLA (first response +
resolution). Kept apart from tests.py, which is already long; Django's
runner picks up any tests*.py module in the app.
"""

from datetime import timedelta

from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import User
from apps.departments.models import Department
from apps.guests.models import Guest
from apps.rooms.models import Room

from .models import Category, Ticket, TicketHistory
from .services import (
    auto_assign,
    compute_admin_stats_summary,
    compute_department_stats_summary,
    pick_auto_assignee,
)


class WorkflowTestData:
    @classmethod
    def setUpTestData(cls):
        cls.department = Department.objects.create(name="Housekeeping", code="HK_WF", auto_assign=True)
        cls.other_department = Department.objects.create(name="Maintenance", code="MT_WF", auto_assign=True)
        cls.category = Category.objects.create(
            name="Towels", code="TOWELS_WF", sla_minutes=30, response_sla_minutes=10
        )
        cls.room = Room.objects.create(number="WF1", status=Room.Status.OCCUPIED)
        cls.guest_user = User.objects.create_user(username="wf_guest", role=User.Role.GUEST)
        cls.guest = Guest.objects.create(
            user=cls.guest_user, full_name="Guest", national_id="0055544433", phone="", room=cls.room
        )

    def operator(self, username, *, seen_ago=timedelta(seconds=5), supervisor=False, department=None):
        return User.objects.create_user(
            username=username,
            role=User.Role.OPERATOR,
            department=department or self.department,
            is_supervisor=supervisor,
            last_seen_at=None if seen_ago is None else timezone.now() - seen_ago,
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


class AutoAssignTests(WorkflowTestData, TestCase):
    def test_goes_to_the_operator_with_the_fewest_active_tickets(self):
        busy = self.operator("wf_busy")
        idle = self.operator("wf_idle")
        self.ticket(assigned_to=busy, status=Ticket.Status.IN_PROGRESS)

        self.assertEqual(pick_auto_assignee(self.department), idle)

    def test_finished_tickets_do_not_count_as_workload(self):
        a = self.operator("wf_a")
        b = self.operator("wf_b")
        self.ticket(assigned_to=a, status=Ticket.Status.RESOLVED, resolution="Done")
        self.ticket(assigned_to=b, status=Ticket.Status.IN_PROGRESS)

        self.assertEqual(pick_auto_assignee(self.department), a)

    def test_only_operators_with_the_panel_open_are_picked(self):
        self.operator("wf_gone_home", seen_ago=timedelta(hours=3))
        self.operator("wf_never_logged_in", seen_ago=None)

        self.assertIsNone(pick_auto_assignee(self.department))

    @override_settings(OPERATOR_PRESENCE_SECONDS=600)
    def test_presence_window_is_configurable(self):
        recent = self.operator("wf_recent", seen_ago=timedelta(minutes=5))

        self.assertEqual(pick_auto_assignee(self.department), recent)

    def test_regular_operators_before_the_supervisor_on_a_tie(self):
        self.operator("wf_aaa_sup", supervisor=True)
        regular = self.operator("wf_zzz_regular")

        self.assertEqual(pick_auto_assignee(self.department), regular)

    def test_never_picks_another_departments_operator(self):
        self.operator("wf_other", department=self.other_department)

        self.assertIsNone(pick_auto_assignee(self.department))

    def test_assigns_logs_and_keeps_the_ticket_open(self):
        operator = self.operator("wf_op")
        ticket = self.ticket()

        self.assertEqual(auto_assign(ticket), operator)

        ticket.refresh_from_db()
        self.assertEqual(ticket.assigned_to, operator)
        # Assigned but not started: the operator still has to respond.
        self.assertEqual(ticket.status, Ticket.Status.OPEN)
        self.assertIsNone(ticket.first_response_at)
        entry = TicketHistory.objects.get(ticket=ticket, action=TicketHistory.Action.ASSIGNED)
        self.assertIsNone(entry.user)  # the system did it
        self.assertEqual(entry.new_value, "wf_op")

    def test_department_switch_off_leaves_it_for_the_supervisor(self):
        self.operator("wf_op")
        self.department.auto_assign = False
        self.department.save()

        ticket = self.ticket()

        self.assertIsNone(auto_assign(ticket))
        ticket.refresh_from_db()
        self.assertIsNone(ticket.assigned_to)

    def test_an_already_assigned_ticket_is_left_alone(self):
        self.operator("wf_op")
        chosen = self.operator("wf_chosen", seen_ago=timedelta(hours=5))
        ticket = self.ticket(assigned_to=chosen)

        self.assertIsNone(auto_assign(ticket))


class AutoAssignOnGuestCreateTests(WorkflowTestData, APITestCase):
    def create_ticket(self):
        self.client.force_authenticate(self.guest_user)
        return self.client.post(
            reverse("tickets:guest-ticket-list-create"),
            {
                "title": "Towels",
                "description": "Two, please.",
                "department": self.department.pk,
                "category": self.category.pk,
            },
            format="json",
        )

    def test_a_new_guest_ticket_is_auto_assigned_and_the_operator_becomes_busy(self):
        operator = self.operator("wf_op")

        response = self.create_ticket()

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        ticket = Ticket.objects.get(pk=response.data["id"])
        self.assertEqual(ticket.assigned_to, operator)

        self.client.force_authenticate(operator)
        me = self.client.get(reverse("accounts:operator-availability"))
        self.assertEqual(me.data, {"is_available": False, "active_tickets": 1})

    def test_consecutive_tickets_spread_across_the_team(self):
        first = self.operator("wf_first")
        second = self.operator("wf_second")

        a = Ticket.objects.get(pk=self.create_ticket().data["id"])
        b = Ticket.objects.get(pk=self.create_ticket().data["id"])

        self.assertEqual({a.assigned_to, b.assigned_to}, {first, second})

    def test_checking_status_counts_as_being_present(self):
        operator = self.operator("wf_op", seen_ago=None)
        self.client.force_authenticate(operator)
        self.client.get(reverse("accounts:operator-availability"))

        response = self.create_ticket()

        self.assertEqual(Ticket.objects.get(pk=response.data["id"]).assigned_to, operator)


class FirstResponseTests(WorkflowTestData, APITestCase):
    def test_first_move_to_in_progress_is_the_first_response(self):
        supervisor = self.operator("wf_sup", supervisor=True)
        ticket = self.ticket(assigned_to=supervisor)
        self.client.force_authenticate(supervisor)

        before = timezone.now()
        self.client.patch(
            reverse("tickets:operator-ticket-detail", kwargs={"pk": ticket.pk}),
            {"status": "IN_PROGRESS"},
            format="json",
        )

        ticket.refresh_from_db()
        self.assertGreaterEqual(ticket.first_response_at, before)

    def test_the_assign_endpoint_counts_too(self):
        supervisor = self.operator("wf_sup", supervisor=True)
        ticket = self.ticket()
        self.client.force_authenticate(supervisor)

        self.client.post(reverse("tickets:operator-ticket-assign", kwargs={"pk": ticket.pk}))

        ticket.refresh_from_db()
        self.assertIsNotNone(ticket.first_response_at)

    def test_handing_back_and_restarting_keeps_the_first_time(self):
        ticket = self.ticket(status=Ticket.Status.IN_PROGRESS)
        first = ticket.first_response_at

        ticket.status = Ticket.Status.OPEN
        ticket.save()
        ticket.status = Ticket.Status.IN_PROGRESS
        ticket.save()

        ticket.refresh_from_db()
        self.assertEqual(ticket.first_response_at, first)

    def test_response_overdue_only_while_nobody_has_started(self):
        waiting = self.ticket()
        Ticket.objects.filter(pk=waiting.pk).update(created_at=timezone.now() - timedelta(minutes=11))
        waiting.refresh_from_db()
        self.assertTrue(waiting.is_response_overdue)

        waiting.status = Ticket.Status.IN_PROGRESS
        waiting.save()
        self.assertFalse(waiting.is_response_overdue)

    def test_response_target_never_exceeds_the_resolution_target(self):
        quick = Category.objects.create(
            name="Wake-up", code="WAKE_WF", sla_minutes=5, response_sla_minutes=10
        )
        ticket = self.ticket(category=quick)

        self.assertEqual(ticket.response_sla_minutes, 5)

    def test_operator_api_exposes_the_response_fields(self):
        supervisor = self.operator("wf_sup", supervisor=True)
        ticket = self.ticket()
        self.client.force_authenticate(supervisor)

        data = self.client.get(reverse("tickets:operator-ticket-detail", kwargs={"pk": ticket.pk})).data

        self.assertIn("response_deadline", data)
        self.assertFalse(data["is_response_overdue"])
        self.assertIsNone(data["first_response_at"])


class SLAStatsTests(WorkflowTestData, TestCase):
    def aged(self, minutes, **kwargs):
        ticket = self.ticket(**kwargs)
        Ticket.objects.filter(pk=ticket.pk).update(created_at=timezone.now() - timedelta(minutes=minutes))
        ticket.refresh_from_db()
        return ticket

    def test_first_response_and_resolution_sla_figures(self):
        # Responded in 5 min (met), resolved in 20 (met).
        met = self.aged(60)
        Ticket.objects.filter(pk=met.pk).update(
            first_response_at=met.created_at + timedelta(minutes=5),
            status=Ticket.Status.RESOLVED,
            resolved_at=met.created_at + timedelta(minutes=20),
        )
        # Responded in 15 min (missed), resolved in 40 (missed).
        late = self.aged(60)
        Ticket.objects.filter(pk=late.pk).update(
            first_response_at=late.created_at + timedelta(minutes=15),
            status=Ticket.Status.RESOLVED,
            resolved_at=late.created_at + timedelta(minutes=40),
        )
        # Nobody started for 12 min: response missed, resolution not due yet.
        self.aged(12)
        # Brand new: nothing due yet.
        self.ticket()

        stats = compute_department_stats_summary(self.department)

        self.assertEqual(stats["response_sla_met_percent"], round(1 / 3 * 100, 1))
        self.assertEqual(stats["resolution_sla_met_percent"], 50.0)
        self.assertEqual(stats["avg_first_response_minutes"], 10.0)
        self.assertEqual(stats["response_overdue_count"], 1)

    def test_nothing_due_means_no_percentage_rather_than_zero(self):
        self.ticket()

        stats = compute_admin_stats_summary()

        self.assertIsNone(stats["response_sla_met_percent"])
        self.assertIsNone(stats["resolution_sla_met_percent"])
        self.assertIsNone(stats["avg_first_response_minutes"])

    def test_cancelled_before_anyone_started_is_not_counted(self):
        self.aged(60, status=Ticket.Status.CANCELLED)

        self.assertIsNone(compute_admin_stats_summary()["response_sla_met_percent"])
