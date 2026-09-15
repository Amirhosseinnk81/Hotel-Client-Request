from rest_framework import viewsets

from .models import (
    DepartmentRequest,
    Goal,
    Process,
    Project,
    RoomDailyStat,
    Task,
)
from .permissions import IsITStaff
from .serializers import (
    DepartmentRequestSerializer,
    GoalSerializer,
    ProcessSerializer,
    ProjectSerializer,
    RoomDailyStatSerializer,
    TaskSerializer,
)


class ProcessViewSet(viewsets.ModelViewSet):
    serializer_class = ProcessSerializer
    permission_classes = [IsITStaff]

    def get_queryset(self):
        qs = Process.objects.all()
        params = self.request.query_params
        if value := params.get("status"):
            qs = qs.filter(status=value)
        if value := params.get("process_type"):
            qs = qs.filter(process_type=value)
        if value := params.get("department"):
            qs = qs.filter(department=value)
        if value := params.get("responsible"):
            qs = qs.filter(responsible_id=value)
        if value := params.get("due_before"):
            qs = qs.filter(next_due_at__lte=value)
        if value := params.get("due_after"):
            qs = qs.filter(next_due_at__gte=value)
        return qs


class ProjectViewSet(viewsets.ModelViewSet):
    serializer_class = ProjectSerializer
    permission_classes = [IsITStaff]

    def get_queryset(self):
        qs = Project.objects.all()
        params = self.request.query_params
        if value := params.get("status"):
            qs = qs.filter(status=value)
        if value := params.get("priority"):
            qs = qs.filter(priority=value)
        if value := params.get("owner"):
            qs = qs.filter(owner_id=value)
        if value := params.get("due_before"):
            qs = qs.filter(due_date__lte=value)
        if value := params.get("due_after"):
            qs = qs.filter(due_date__gte=value)
        return qs


class DepartmentRequestViewSet(viewsets.ModelViewSet):
    serializer_class = DepartmentRequestSerializer
    permission_classes = [IsITStaff]

    def get_queryset(self):
        qs = DepartmentRequest.objects.all()
        params = self.request.query_params
        if value := params.get("status"):
            qs = qs.filter(status=value)
        if value := params.get("priority"):
            qs = qs.filter(priority=value)
        if value := params.get("department"):
            qs = qs.filter(requesting_department=value)
        if value := params.get("assigned_to"):
            qs = qs.filter(assigned_to_id=value)
        return qs


class GoalViewSet(viewsets.ModelViewSet):
    serializer_class = GoalSerializer
    permission_classes = [IsITStaff]

    def get_queryset(self):
        qs = Goal.objects.all()
        params = self.request.query_params
        if value := params.get("status"):
            qs = qs.filter(status=value)
        if value := params.get("goal_type"):
            qs = qs.filter(goal_type=value)
        if value := params.get("owner"):
            qs = qs.filter(owner_id=value)
        return qs


class TaskViewSet(viewsets.ModelViewSet):
    serializer_class = TaskSerializer
    permission_classes = [IsITStaff]

    def get_queryset(self):
        qs = Task.objects.all()
        params = self.request.query_params
        if value := params.get("status"):
            qs = qs.filter(status=value)
        if value := params.get("priority"):
            qs = qs.filter(priority=value)
        if value := params.get("assigned_to"):
            qs = qs.filter(assigned_to_id=value)
        if value := params.get("due_before"):
            qs = qs.filter(due_date__lte=value)
        if value := params.get("due_after"):
            qs = qs.filter(due_date__gte=value)
        return qs


class RoomDailyStatViewSet(viewsets.ModelViewSet):
    serializer_class = RoomDailyStatSerializer
    permission_classes = [IsITStaff]

    def get_queryset(self):
        qs = RoomDailyStat.objects.all()
        params = self.request.query_params
        if value := params.get("date_from"):
            qs = qs.filter(date__gte=value)
        if value := params.get("date_to"):
            qs = qs.filter(date__lte=value)
        return qs
