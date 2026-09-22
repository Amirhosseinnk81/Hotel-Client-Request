"""
Query-string filters for the IT Ops lists. django-filter (already the
project's DEFAULT_FILTER_BACKENDS) validates each value, so a malformed
date is answered 400 instead of reaching the ORM and turning into a 500.
Parameter names are the ones the API has used since Phase 2.
"""

import django_filters

from .models import DepartmentRequest, Goal, Process, Project, RoomDailyStat, Task


class ProcessFilter(django_filters.FilterSet):
    responsible = django_filters.NumberFilter(field_name="responsible_id")
    due_before = django_filters.IsoDateTimeFilter(field_name="next_due_at", lookup_expr="lte")
    due_after = django_filters.IsoDateTimeFilter(field_name="next_due_at", lookup_expr="gte")

    class Meta:
        model = Process
        fields = ["status", "process_type", "frequency", "department", "responsible"]


class ProjectFilter(django_filters.FilterSet):
    owner = django_filters.NumberFilter(field_name="owner_id")
    due_before = django_filters.DateFilter(field_name="due_date", lookup_expr="lte")
    due_after = django_filters.DateFilter(field_name="due_date", lookup_expr="gte")

    class Meta:
        model = Project
        fields = ["status", "priority", "owner"]


class DepartmentRequestFilter(django_filters.FilterSet):
    department = django_filters.NumberFilter(field_name="requesting_department_id")
    assigned_to = django_filters.NumberFilter(field_name="assigned_to_id")

    class Meta:
        model = DepartmentRequest
        fields = ["status", "priority", "department", "assigned_to"]


class GoalFilter(django_filters.FilterSet):
    owner = django_filters.NumberFilter(field_name="owner_id")

    class Meta:
        model = Goal
        fields = ["status", "goal_type", "owner", "related_project"]


class TaskFilter(django_filters.FilterSet):
    assigned_to = django_filters.NumberFilter(field_name="assigned_to_id")
    due_before = django_filters.IsoDateTimeFilter(field_name="due_date", lookup_expr="lte")
    due_after = django_filters.IsoDateTimeFilter(field_name="due_date", lookup_expr="gte")

    class Meta:
        model = Task
        fields = [
            "status",
            "priority",
            "assigned_to",
            "related_process",
            "related_project",
            "related_request",
        ]


class RoomDailyStatFilter(django_filters.FilterSet):
    date_from = django_filters.DateFilter(field_name="date", lookup_expr="gte")
    date_to = django_filters.DateFilter(field_name="date", lookup_expr="lte")

    class Meta:
        model = RoomDailyStat
        fields = []
