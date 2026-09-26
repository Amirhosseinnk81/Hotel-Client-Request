import io
from datetime import date, datetime, timedelta
from io import StringIO

from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import User
from apps.departments.models import Department
from apps.rooms.models import Room, RoomStatusLog

from PIL import Image

from .models import (
    DepartmentRequest,
    ITRequestTemplate,
    Process,
    Project,
    RoomDailyStat,
    Task,
)
from .services import compute_room_stats, snapshot_room_stats


class ITOpsTestData:
    """Shared cast: an IT department with a supervisor and two operators,
    plus a housekeeping supervisor, an admin and a guest who are not IT."""

    @classmethod
    def setUpTestData(cls):
        cls.it = Department.objects.create(name="IT", code="IT")
        cls.housekeeping = Department.objects.create(name="Housekeeping", code="HK_ITOPS")

        cls.it_supervisor = User.objects.create_user(
            username="it_sup", role=User.Role.OPERATOR, department=cls.it, is_supervisor=True
        )
        cls.it_operator = User.objects.create_user(
            username="it_op", role=User.Role.OPERATOR, department=cls.it
        )
        cls.it_colleague = User.objects.create_user(
            username="it_op2", role=User.Role.OPERATOR, department=cls.it
        )
        cls.hk_supervisor = User.objects.create_user(
            username="hk_sup",
            role=User.Role.OPERATOR,
            department=cls.housekeeping,
            is_supervisor=True,
        )
        cls.admin = User.objects.create_user(username="itops_admin", role=User.Role.ADMIN)
        cls.guest = User.objects.create_user(username="itops_guest", role=User.Role.GUEST)

    def as_user(self, user):
        self.client.force_authenticate(user)

    def make_task(self, **kwargs):
        defaults = {"title": "Replace switch", "assigned_to": self.it_operator}
        defaults.update(kwargs)
        return Task.objects.create(**defaults)

    def make_request(self, **kwargs):
        defaults = {
            "title": "New printer for front desk",
            "requesting_department": self.housekeeping,
            "assigned_to": self.it_operator,
        }
        defaults.update(kwargs)
        return DepartmentRequest.objects.create(**defaults)


class ITOpsAccessTests(ITOpsTestData, APITestCase):
    """Only IT operators and admins get in — for reading too."""

    def test_it_operator_and_admin_can_read(self):
        for user in (self.it_operator, self.it_supervisor, self.admin):
            self.as_user(user)
            with self.subTest(user=user.username):
                self.assertEqual(
                    self.client.get(reverse("it_ops:task-list")).status_code, status.HTTP_200_OK
                )
                self.assertEqual(
                    self.client.get(reverse("it_ops:today-dashboard")).status_code,
                    status.HTTP_200_OK,
                )

    def test_operator_of_another_department_is_refused_even_for_reading(self):
        # A housekeeping *supervisor* is still not IT staff.
        self.as_user(self.hk_supervisor)

        for name in ("it_ops:task-list", "it_ops:process-list", "it_ops:today-dashboard"):
            with self.subTest(url=name):
                self.assertEqual(
                    self.client.get(reverse(name)).status_code, status.HTTP_403_FORBIDDEN
                )

    def test_guest_is_refused_and_anonymous_is_unauthenticated(self):
        self.as_user(self.guest)
        self.assertEqual(
            self.client.get(reverse("it_ops:task-list")).status_code, status.HTTP_403_FORBIDDEN
        )

        self.client.force_authenticate(None)
        self.assertEqual(
            self.client.get(reverse("it_ops:task-list")).status_code,
            status.HTTP_401_UNAUTHORIZED,
        )

    def test_moving_an_operator_out_of_it_takes_effect_immediately(self):
        # Read from the database on every request, never from a token claim.
        mover = User.objects.create_user(
            username="it_mover", role=User.Role.OPERATOR, department=self.it
        )
        self.as_user(mover)
        self.assertEqual(self.client.get(reverse("it_ops:task-list")).status_code, 200)

        mover.department = self.housekeeping
        mover.save()

        self.assertEqual(self.client.get(reverse("it_ops:task-list")).status_code, 403)

    def test_routes_live_under_api_v1(self):
        self.assertEqual(reverse("it_ops:today-dashboard"), "/api/v1/it-ops/today/")
        self.assertEqual(reverse("it_ops:task-list"), "/api/v1/it-ops/tasks/")


class ITSupervisorOnlyTests(ITOpsTestData, APITestCase):
    def test_regular_it_operator_cannot_create_projects_goals_or_processes(self):
        self.as_user(self.it_operator)

        cases = [
            ("it_ops:project-list", {"title": "Wi-Fi upgrade"}),
            ("it_ops:goal-list", {"title": "99.9% uptime", "goal_type": "LONG_TERM"}),
            ("it_ops:process-list", {"title": "Backups", "process_type": "PERIODIC_SERVICE"}),
        ]
        for name, body in cases:
            with self.subTest(url=name):
                response = self.client.post(reverse(name), body, format="json")
                self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_it_supervisor_and_admin_can_create_projects(self):
        for user in (self.it_supervisor, self.admin):
            self.as_user(user)
            with self.subTest(user=user.username):
                response = self.client.post(
                    reverse("it_ops:project-list"),
                    {"title": f"Upgrade by {user.username}", "owner": user.pk},
                    format="json",
                )
                self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_regular_it_operator_cannot_delete_even_their_own_task(self):
        task = self.make_task()
        self.as_user(self.it_operator)

        response = self.client.delete(reverse("it_ops:task-detail", args=[task.pk]))

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertTrue(Task.objects.filter(pk=task.pk).exists())

    def test_supervisor_can_delete(self):
        task = self.make_task()
        self.as_user(self.it_supervisor)

        response = self.client.delete(reverse("it_ops:task-detail", args=[task.pk]))

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_project_due_date_cannot_precede_start(self):
        self.as_user(self.it_supervisor)

        response = self.client.post(
            reverse("it_ops:project-list"),
            {"title": "Backwards", "start_date": "2026-05-10", "due_date": "2026-05-01"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class ITTaskTests(ITOpsTestData, APITestCase):
    def test_regular_operator_creating_a_task_gets_it_themselves(self):
        self.as_user(self.it_operator)

        response = self.client.post(
            reverse("it_ops:task-list"), {"title": "Check cabling"}, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        task = Task.objects.get(pk=response.data["id"])
        self.assertEqual(task.assigned_to, self.it_operator)
        self.assertEqual(task.assigned_by, self.it_operator)

    def test_regular_operator_cannot_assign_a_task_to_a_colleague(self):
        self.as_user(self.it_operator)

        response = self.client.post(
            reverse("it_ops:task-list"),
            {"title": "Your problem now", "assigned_to": self.it_colleague.pk},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_assigned_by_cannot_be_forged(self):
        self.as_user(self.it_supervisor)

        response = self.client.post(
            reverse("it_ops:task-list"),
            {"title": "Patch servers", "assigned_to": self.it_operator.pk, "assigned_by": self.admin.pk},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Task.objects.get(pk=response.data["id"]).assigned_by, self.it_supervisor)

    def test_operator_works_on_own_task_but_not_on_others(self):
        mine = self.make_task()
        theirs = self.make_task(assigned_to=self.it_colleague)
        self.as_user(self.it_operator)

        ok = self.client.patch(
            reverse("it_ops:task-detail", args=[mine.pk]), {"status": "DONE"}, format="json"
        )
        refused = self.client.patch(
            reverse("it_ops:task-detail", args=[theirs.pk]), {"status": "DONE"}, format="json"
        )

        self.assertEqual(ok.status_code, status.HTTP_200_OK)
        self.assertEqual(refused.status_code, status.HTTP_403_FORBIDDEN)

    def test_operator_cannot_reprioritise_or_hand_off_own_task(self):
        mine = self.make_task()
        self.as_user(self.it_operator)

        for body in ({"priority": "CRITICAL"}, {"assigned_to": self.it_colleague.pk}):
            with self.subTest(body=body):
                response = self.client.patch(
                    reverse("it_ops:task-detail", args=[mine.pk]), body, format="json"
                )
                self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_work_can_only_go_to_it_operators(self):
        self.as_user(self.it_supervisor)

        for outsider in (self.hk_supervisor, self.admin, self.guest):
            with self.subTest(user=outsider.username):
                response = self.client.post(
                    reverse("it_ops:task-list"),
                    {"title": "Misrouted", "assigned_to": outsider.pk},
                    format="json",
                )
                self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_malformed_date_filter_is_a_400_not_a_500(self):
        self.as_user(self.it_operator)

        response = self.client.get(reverse("it_ops:task-list"), {"due_before": "not-a-date"})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_filter_by_assignee(self):
        self.make_task()
        self.make_task(assigned_to=self.it_colleague)
        self.as_user(self.it_operator)

        response = self.client.get(
            reverse("it_ops:task-list"), {"assigned_to": self.it_colleague.pk}
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 1)


class ITDepartmentRequestTests(ITOpsTestData, APITestCase):
    def test_any_it_operator_can_log_a_request_with_its_urgency(self):
        self.as_user(self.it_operator)

        response = self.client.post(
            reverse("it_ops:department-request-list"),
            {
                "title": "Card reader down",
                "requesting_department": self.housekeeping.pk,
                "priority": "HIGH",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["requesting_department_name"], "Housekeeping")
        self.assertEqual(response.data["priority"], "HIGH")

    def test_requesting_department_is_required(self):
        self.as_user(self.it_supervisor)

        response = self.client.post(
            reverse("it_ops:department-request-list"), {"title": "From nowhere"}, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("requesting_department", response.data["errors"])

    def test_assignee_completes_and_resolved_at_follows_the_status(self):
        request = self.make_request(status=DepartmentRequest.Status.IN_PROGRESS)
        self.as_user(self.it_operator)

        response = self.client.patch(
            reverse("it_ops:department-request-detail", args=[request.pk]),
            {"status": "COMPLETED"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        request.refresh_from_db()
        self.assertIsNotNone(request.resolved_at)

        # Reopened (by the supervisor): no longer resolved.
        self.as_user(self.it_supervisor)
        self.client.patch(
            reverse("it_ops:department-request-detail", args=[request.pk]),
            {"status": "IN_PROGRESS"},
            format="json",
        )
        request.refresh_from_db()
        self.assertIsNone(request.resolved_at)

    def test_only_the_supervisor_can_reject(self):
        request = self.make_request()
        url = reverse("it_ops:department-request-detail", args=[request.pk])

        self.as_user(self.it_operator)
        refused = self.client.patch(url, {"status": "REJECTED"}, format="json")
        self.assertEqual(refused.status_code, status.HTTP_403_FORBIDDEN)

        self.as_user(self.it_supervisor)
        allowed = self.client.patch(url, {"status": "REJECTED"}, format="json")
        self.assertEqual(allowed.status_code, status.HTTP_200_OK)

    def test_regular_operator_cannot_file_a_request_as_rejected(self):
        self.as_user(self.it_operator)

        response = self.client.post(
            reverse("it_ops:department-request-list"),
            {"title": "x", "requesting_department": self.housekeeping.pk, "status": "REJECTED"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_list_puts_the_most_urgent_first_not_alphabetical(self):
        # Alphabetically descending would be MEDIUM, LOW, HIGH, CRITICAL.
        for priority in ("MEDIUM", "LOW", "CRITICAL", "HIGH"):
            self.make_request(title=priority, priority=priority)
        self.as_user(self.it_operator)

        response = self.client.get(reverse("it_ops:department-request-list"))

        self.assertEqual(
            [row["priority"] for row in response.data["results"]],
            ["CRITICAL", "HIGH", "MEDIUM", "LOW"],
        )


class ProcessScheduleTests(ITOpsTestData, APITestCase):
    """Phase 4 — next_due_at is calculated, not typed in."""

    def make_process(self, **kwargs):
        defaults = {
            "title": "Nightly backup",
            "process_type": Process.ProcessType.PERIODIC_SERVICE,
            "frequency": Process.Frequency.DAILY,
            "responsible": self.it_operator,
        }
        defaults.update(kwargs)
        return Process.objects.create(**defaults)

    def test_new_recurring_process_gets_a_due_date(self):
        before = timezone.now()
        process = self.make_process(frequency=Process.Frequency.WEEKLY)

        self.assertGreaterEqual(process.next_due_at, before + timedelta(weeks=1))
        self.assertLess(process.next_due_at, timezone.now() + timedelta(weeks=1, minutes=1))

    def test_due_date_counts_from_last_done_when_given(self):
        done = timezone.make_aware(datetime(2026, 3, 10, 9, 0))
        process = self.make_process(last_done_at=done)

        self.assertEqual(process.next_due_at, done + timedelta(days=1))

    def test_monthly_clamps_to_the_end_of_a_shorter_month(self):
        done = timezone.make_aware(datetime(2026, 1, 31, 8, 0))
        process = self.make_process(frequency=Process.Frequency.MONTHLY, last_done_at=done)

        self.assertEqual(process.next_due_at, timezone.make_aware(datetime(2026, 2, 28, 8, 0)))

    def test_quarterly_and_yearly(self):
        done = timezone.make_aware(datetime(2026, 11, 15, 8, 0))
        quarterly = self.make_process(frequency=Process.Frequency.QUARTERLY, last_done_at=done)
        yearly = self.make_process(frequency=Process.Frequency.YEARLY, last_done_at=done)

        self.assertEqual(quarterly.next_due_at, timezone.make_aware(datetime(2027, 2, 15, 8, 0)))
        self.assertEqual(yearly.next_due_at, timezone.make_aware(datetime(2027, 11, 15, 8, 0)))

    def test_a_hand_postponed_run_is_kept_on_unrelated_edits(self):
        process = self.make_process()
        postponed = timezone.now() + timedelta(days=5)
        process.next_due_at = postponed
        process.save()

        process.description = "Now with offsite copy"
        process.save()

        process.refresh_from_db()
        self.assertEqual(process.next_due_at, postponed)

    def test_changing_the_frequency_recalculates(self):
        done = timezone.make_aware(datetime(2026, 4, 1, 8, 0))
        process = self.make_process(last_done_at=done)

        process.frequency = Process.Frequency.WEEKLY
        process.save()

        self.assertEqual(process.next_due_at, done + timedelta(weeks=1))

    def test_one_off_process_is_never_touched(self):
        process = self.make_process(frequency=Process.Frequency.NONE)
        self.assertIsNone(process.next_due_at)

        process.last_done_at = timezone.now()
        process.save()
        self.assertIsNone(process.next_due_at)

    def test_responsible_marks_it_done_and_the_next_run_moves_on(self):
        process = self.make_process()
        self.as_user(self.it_operator)

        before = timezone.now()
        response = self.client.post(reverse("it_ops:process-mark-done", args=[process.pk]))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        process.refresh_from_db()
        self.assertGreaterEqual(process.last_done_at, before)
        self.assertEqual(process.next_due_at, process.last_done_at + timedelta(days=1))

    def test_someone_else_cannot_mark_it_done(self):
        process = self.make_process()
        self.as_user(self.it_colleague)

        response = self.client.post(reverse("it_ops:process-mark-done", args=[process.pk]))

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_responsible_cannot_rewrite_the_process_itself(self):
        process = self.make_process()
        self.as_user(self.it_operator)

        response = self.client.patch(
            reverse("it_ops:process-detail", args=[process.pk]),
            {"frequency": "YEARLY"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class RoomStatsTests(ITOpsTestData, APITestCase):
    """Phase 5 — occupancy comes from Room data, never typed in."""

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.r1 = Room.objects.create(number="R1", status=Room.Status.OCCUPIED)
        cls.r2 = Room.objects.create(number="R2", status=Room.Status.AVAILABLE)
        cls.r3 = Room.objects.create(number="R3", status=Room.Status.MAINTENANCE)
        cls.r4 = Room.objects.create(number="R4", status=Room.Status.OCCUPIED)

    def test_today_is_the_live_room_status(self):
        stats = compute_room_stats()

        self.assertEqual(
            (stats["total_rooms"], stats["occupied_rooms"], stats["vacant_rooms"], stats["out_of_order_rooms"]),
            (4, 2, 1, 1),
        )

    def test_a_past_day_is_rebuilt_from_the_status_log(self):
        yesterday = timezone.localdate() - timedelta(days=1)
        noon_yesterday = timezone.make_aware(datetime.combine(yesterday, datetime.min.time())) + timedelta(hours=12)

        # R2 was checked out this morning (OCCUPIED -> AVAILABLE today):
        # yesterday it was still occupied.
        self.r2.status = Room.Status.OCCUPIED
        self.r2.save()
        self.r2.status = Room.Status.AVAILABLE
        self.r2.save()
        RoomStatusLog.objects.filter(room=self.r2, new_status=Room.Status.OCCUPIED).update(
            changed_at=noon_yesterday - timedelta(days=3)
        )
        RoomStatusLog.objects.filter(room=self.r2, new_status=Room.Status.AVAILABLE).update(
            changed_at=timezone.now()
        )
        # R3 went into maintenance only today; yesterday it was available.
        RoomStatusLog.objects.create(
            room=self.r3,
            previous_status=Room.Status.AVAILABLE,
            new_status=Room.Status.MAINTENANCE,
        )

        stats = compute_room_stats(yesterday)

        # R1, R4 (never changed) and R2 occupied; R3 available.
        self.assertEqual(stats["occupied_rooms"], 3)
        self.assertEqual(stats["vacant_rooms"], 1)
        self.assertEqual(stats["out_of_order_rooms"], 0)

    def test_snapshot_updates_the_day_instead_of_duplicating(self):
        first = snapshot_room_stats()
        self.r2.status = Room.Status.OCCUPIED
        self.r2.save()
        second = snapshot_room_stats()

        self.assertEqual(first.pk, second.pk)
        self.assertEqual(RoomDailyStat.objects.count(), 1)
        self.assertEqual(second.occupied_rooms, 3)
        self.assertEqual(second.occupancy_rate, 75.0)

    def test_snapshot_endpoint_is_supervisor_only(self):
        url = reverse("it_ops:room-stat-snapshot")

        self.as_user(self.it_operator)
        self.assertEqual(self.client.post(url).status_code, status.HTTP_403_FORBIDDEN)

        self.as_user(self.it_supervisor)
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["total_rooms"], 4)

    def test_snapshot_refuses_a_future_day(self):
        self.as_user(self.it_supervisor)
        tomorrow = timezone.localdate() + timedelta(days=1)

        response = self.client.post(
            reverse("it_ops:room-stat-snapshot"), {"date": tomorrow.isoformat()}, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_stats_cannot_be_typed_in_by_hand(self):
        self.as_user(self.it_supervisor)

        response = self.client.post(
            reverse("it_ops:room-stat-list"),
            {"date": "2026-01-01", "total_rooms": 999, "occupied_rooms": 999},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_management_command_backfills_days(self):
        call_command("snapshot_room_stats", "--days", "3", stdout=StringIO())

        self.assertEqual(RoomDailyStat.objects.count(), 3)
        self.assertEqual(
            RoomDailyStat.objects.order_by("-date").first().date, timezone.localdate()
        )


class TodayDashboardTests(ITOpsTestData, APITestCase):
    def test_dashboard_shows_what_is_due_and_nothing_that_is_not(self):
        now = timezone.now()
        overdue = self.make_task(title="Overdue", due_date=now - timedelta(days=2))
        self.make_task(title="Done", due_date=now - timedelta(days=1), status=Task.Status.DONE)
        self.make_task(title="Next week", due_date=now + timedelta(days=7))

        due = Process.objects.create(
            title="Due", process_type="PERIODIC_CHECK", next_due_at=now - timedelta(hours=1)
        )
        Process.objects.create(
            title="Paused",
            process_type="PERIODIC_CHECK",
            status=Process.Status.PAUSED,
            next_due_at=now - timedelta(hours=1),
        )

        open_request = self.make_request()
        self.make_request(title="Closed", status=DepartmentRequest.Status.COMPLETED)
        Room.objects.create(number="D1", status=Room.Status.OCCUPIED)

        self.as_user(self.it_operator)
        response = self.client.get(reverse("it_ops:today-dashboard"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data
        self.assertEqual([t["id"] for t in data["tasks_due_or_overdue"]], [overdue.pk])
        self.assertEqual([p["id"] for p in data["processes_due_or_overdue"]], [due.pk])
        self.assertEqual([r["id"] for r in data["open_department_requests"]], [open_request.pk])
        self.assertEqual(data["room_stats_today"]["occupied_rooms"], 1)
        self.assertEqual(data["room_stats_today"]["occupancy_rate"], 100.0)
        # "Overdue" and "Next week" are open and theirs; "Done" is not open.
        self.assertEqual(data["my_open_tasks_count"], 2)


class ProcessDateHelperTests(TestCase):
    def test_leap_year_february(self):
        from .models import _add_months

        self.assertEqual(_add_months(date(2028, 1, 31), 1), date(2028, 2, 29))
        self.assertEqual(_add_months(date(2026, 12, 15), 1), date(2027, 1, 15))


class OutgoingITRequestTests(ITOpsTestData, APITestCase):
    """Any department files requests to IT from its own panel."""

    url = reverse("it_ops:outgoing-request-list")

    def test_department_operator_files_a_request_for_their_own_department(self):
        self.as_user(self.hk_supervisor)

        response = self.client.post(
            self.url,
            {
                "title": "Printer jammed",
                "priority": "HIGH",
                # Attempts to set what isn't theirs are ignored.
                "requesting_department": self.it.pk,
                "status": "COMPLETED",
                "assigned_to": self.it_operator.pk,
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        request = DepartmentRequest.objects.get(pk=response.data["id"])
        self.assertEqual(request.requesting_department, self.housekeeping)
        self.assertEqual(request.requested_by, self.hk_supervisor)
        self.assertEqual(request.status, DepartmentRequest.Status.PENDING)
        self.assertIsNone(request.assigned_to)
        self.assertEqual(request.priority, "HIGH")

    def test_a_regular_operator_can_file_too(self):
        clerk = User.objects.create_user(
            username="hk_clerk", role=User.Role.OPERATOR, department=self.housekeeping
        )
        self.as_user(clerk)

        response = self.client.post(self.url, {"title": "No network"}, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_only_their_own_departments_requests_are_listed(self):
        mine = self.make_request(requesting_department=self.housekeeping)
        front_desk = Department.objects.create(name="Front desk", code="FD_ITOPS")
        self.make_request(requesting_department=front_desk)
        self.as_user(self.hk_supervisor)

        response = self.client.get(self.url)

        self.assertEqual([r["id"] for r in response.data["results"]], [mine.pk])

    def test_another_departments_request_is_not_found(self):
        front_desk = Department.objects.create(name="Front desk", code="FD_ITOPS2")
        theirs = self.make_request(requesting_department=front_desk)
        self.as_user(self.hk_supervisor)

        response = self.client.get(reverse("it_ops:outgoing-request-detail", args=[theirs.pk]))

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_requesters_cannot_change_or_delete_a_filed_request(self):
        mine = self.make_request(requesting_department=self.housekeeping)
        self.as_user(self.hk_supervisor)
        detail = reverse("it_ops:outgoing-request-detail", args=[mine.pk])

        self.assertEqual(
            self.client.patch(detail, {"status": "COMPLETED"}, format="json").status_code,
            status.HTTP_405_METHOD_NOT_ALLOWED,
        )
        self.assertEqual(self.client.delete(detail).status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_filed_request_reaches_it_with_the_requester(self):
        self.as_user(self.hk_supervisor)
        self.client.post(self.url, {"title": "Card reader"}, format="json")

        self.as_user(self.it_operator)
        response = self.client.get(reverse("it_ops:department-request-list"))

        row = response.data["results"][0]
        self.assertEqual(row["requested_by_username"], "hk_sup")
        self.assertEqual(row["requesting_department_name"], "Housekeeping")

    def test_admin_guest_and_departmentless_operator_are_refused(self):
        drifter = User.objects.create_user(username="no_dept_op", role=User.Role.OPERATOR)
        for user in (self.admin, self.guest, drifter):
            self.as_user(user)
            with self.subTest(user=user.username):
                self.assertEqual(self.client.get(self.url).status_code, status.HTTP_403_FORBIDDEN)


class ITStaffListTests(ITOpsTestData, APITestCase):
    def test_lists_it_operators_supervisor_first(self):
        self.as_user(self.it_operator)

        response = self.client.get(reverse("it_ops:staff"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual([m["username"] for m in response.data], ["it_sup", "it_op", "it_op2"])

    def test_other_departments_cannot_list_it_staff(self):
        self.as_user(self.hk_supervisor)

        self.assertEqual(self.client.get(reverse("it_ops:staff")).status_code, 403)

def png_upload(name="problem.png"):
    """A tiny real PNG — ImageField rejects anything Pillow cannot open."""
    buffer = io.BytesIO()
    Image.new("RGB", (8, 8), (200, 160, 120)).save(buffer, format="PNG")
    buffer.seek(0)
    return SimpleUploadedFile(name, buffer.read(), content_type="image/png")


class ITRequestTemplateTests(ITOpsTestData, APITestCase):
    """
    One-click shortcuts on the "ask IT" form — the staff-side twin of the
    guest's quick requests.
    """

    url = reverse("it_ops:request-templates")

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        ITRequestTemplate.objects.create(
            title="پرینتر کار نمی‌کند",
            description="روشن است ولی چاپ نمی‌کند.",
            icon="Printer",
            priority="HIGH",
            order=0,
        )
        ITRequestTemplate.objects.create(title="نصب نرم‌افزار", priority="LOW", order=1)
        ITRequestTemplate.objects.create(title="قالب بازنشسته", is_active=False, order=2)

    def test_any_operator_with_a_department_sees_the_active_templates(self):
        self.as_user(self.hk_supervisor)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            [t["title"] for t in response.data], ["پرینتر کار نمی‌کند", "نصب نرم‌افزار"]
        )

    def test_a_template_carries_what_it_should_fill_in(self):
        self.as_user(self.hk_supervisor)

        first = self.client.get(self.url).data[0]

        self.assertEqual(first["description"], "روشن است ولی چاپ نمی‌کند.")
        self.assertEqual(first["priority"], "HIGH")
        self.assertEqual(first["icon"], "Printer")

    def test_they_are_read_only_over_the_api(self):
        self.as_user(self.hk_supervisor)

        response = self.client.post(self.url, {"title": "از راه دور"}, format="json")

        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_a_guest_or_a_department_less_operator_gets_nothing(self):
        drifter = User.objects.create_user(username="tpl_no_dept", role=User.Role.OPERATOR)
        for user in (self.guest, drifter):
            self.as_user(user)
            with self.subTest(user=user.username):
                self.assertEqual(self.client.get(self.url).status_code, 403)


class ITRequestAttachmentTests(ITOpsTestData, APITestCase):
    """A photo of the problem, on a department's own request to IT."""

    def setUp(self):
        self.request = DepartmentRequest.objects.create(
            title="پرینتر",
            requesting_department=self.housekeeping,
            requested_by=self.hk_supervisor,
        )
        self.url = reverse("it_ops:outgoing-request-attachments", args=[self.request.pk])

    def test_the_asking_department_attaches_a_photo(self):
        self.as_user(self.hk_supervisor)

        response = self.client.post(self.url, {"image": png_upload()}, format="multipart")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(self.request.attachments.count(), 1)
        self.assertEqual(response.data["uploaded_by_username"], "hk_sup")

    def test_another_department_cannot_attach_to_a_request_that_is_not_theirs(self):
        other = User.objects.create_user(
            username="fd_op",
            role=User.Role.OPERATOR,
            department=Department.objects.create(name="Front desk", code="FD_ITOPS"),
        )
        self.as_user(other)

        response = self.client.post(self.url, {"image": png_upload()}, format="multipart")

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(self.request.attachments.count(), 0)

    def test_a_non_image_is_refused(self):
        self.as_user(self.hk_supervisor)
        not_an_image = SimpleUploadedFile("notes.txt", b"just text", content_type="text/plain")

        response = self.client.post(self.url, {"image": not_an_image}, format="multipart")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_the_photo_comes_back_with_the_request(self):
        self.as_user(self.hk_supervisor)
        self.client.post(self.url, {"image": png_upload()}, format="multipart")

        listed = self.client.get(reverse("it_ops:outgoing-request-list")).data["results"][0]

        self.assertEqual(len(listed["attachments"]), 1)
        self.assertIn("it_request_attachments/", listed["attachments"][0]["image"])

    def test_it_staff_see_the_photo_on_their_own_side(self):
        self.as_user(self.hk_supervisor)
        self.client.post(self.url, {"image": png_upload()}, format="multipart")
        self.as_user(self.it_operator)

        detail = self.client.get(
            reverse("it_ops:department-request-detail", args=[self.request.pk])
        ).data

        self.assertEqual(len(detail["attachments"]), 1)


class ITRequestFeedbackTests(ITOpsTestData, APITestCase):
    """The asking department says how the work went."""

    def setUp(self):
        self.request = DepartmentRequest.objects.create(
            title="پرینتر",
            requesting_department=self.housekeeping,
            requested_by=self.hk_supervisor,
        )
        self.url = reverse("it_ops:outgoing-request-rate", args=[self.request.pk])

    def complete(self):
        self.request.status = DepartmentRequest.Status.COMPLETED
        self.request.save()

    def test_a_completed_request_can_be_rated_with_a_comment(self):
        self.complete()
        self.as_user(self.hk_supervisor)

        response = self.client.post(
            self.url, {"rating": 5, "feedback": "سریع درست شد"}, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.request.refresh_from_db()
        self.assertEqual(self.request.rating, 5)
        self.assertEqual(self.request.feedback, "سریع درست شد")
        self.assertIsNotNone(self.request.rated_at)
        self.assertFalse(response.data["can_be_rated"])

    def test_the_comment_is_optional(self):
        self.complete()
        self.as_user(self.hk_supervisor)

        response = self.client.post(self.url, {"rating": 3}, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.request.refresh_from_db()
        self.assertEqual(self.request.feedback, "")

    def test_work_that_is_not_finished_cannot_be_rated(self):
        self.as_user(self.hk_supervisor)

        response = self.client.post(self.url, {"rating": 5}, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.request.refresh_from_db()
        self.assertIsNone(self.request.rating)

    def test_a_rejected_request_cannot_be_rated(self):
        # IT saying no is a conversation, not a service to score.
        self.request.status = DepartmentRequest.Status.REJECTED
        self.request.save()
        self.as_user(self.hk_supervisor)

        self.assertEqual(
            self.client.post(self.url, {"rating": 1}, format="json").status_code, 400
        )

    def test_rating_happens_once(self):
        self.complete()
        self.as_user(self.hk_supervisor)
        self.client.post(self.url, {"rating": 4}, format="json")

        second = self.client.post(self.url, {"rating": 1}, format="json")

        self.assertEqual(second.status_code, status.HTTP_400_BAD_REQUEST)
        self.request.refresh_from_db()
        self.assertEqual(self.request.rating, 4)

    def test_a_score_outside_one_to_five_is_refused(self):
        self.complete()
        self.as_user(self.hk_supervisor)

        for score in (0, 6):
            with self.subTest(score=score):
                response = self.client.post(self.url, {"rating": score}, format="json")
                self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_another_department_cannot_rate_work_done_for_someone_else(self):
        self.complete()
        other = User.objects.create_user(
            username="fd_op2",
            role=User.Role.OPERATOR,
            department=Department.objects.create(name="Front desk 2", code="FD2_ITOPS"),
        )
        self.as_user(other)

        self.assertEqual(
            self.client.post(self.url, {"rating": 1}, format="json").status_code, 404
        )

    def test_it_cannot_rate_its_own_work_through_the_it_endpoints(self):
        # The feedback fields are read-only on the IT side.
        self.complete()
        self.as_user(self.it_supervisor)

        self.client.patch(
            reverse("it_ops:department-request-detail", args=[self.request.pk]),
            {"rating": 5, "feedback": "عالی بودم"},
            format="json",
        )

        self.request.refresh_from_db()
        self.assertIsNone(self.request.rating)
        self.assertEqual(self.request.feedback, "")

    def test_can_be_rated_tells_the_panel_when_to_offer_the_box(self):
        self.as_user(self.hk_supervisor)
        listed = self.client.get(reverse("it_ops:outgoing-request-list")).data["results"][0]
        self.assertFalse(listed["can_be_rated"])

        self.complete()
        listed = self.client.get(reverse("it_ops:outgoing-request-list")).data["results"][0]
        self.assertTrue(listed["can_be_rated"])

    def test_it_staff_read_the_feedback_they_were_given(self):
        self.complete()
        self.as_user(self.hk_supervisor)
        self.client.post(self.url, {"rating": 2, "feedback": "دیر شد"}, format="json")
        self.as_user(self.it_operator)

        detail = self.client.get(
            reverse("it_ops:department-request-detail", args=[self.request.pk])
        ).data

        self.assertEqual(detail["rating"], 2)
        self.assertEqual(detail["feedback"], "دیر شد")
