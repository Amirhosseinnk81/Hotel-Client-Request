from django.utils import timezone
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import DepartmentRequest, Process, RoomDailyStat, Task
from .permissions import IsITStaff
from .serializers import (
    DepartmentRequestSerializer,
    ProcessSerializer,
    RoomDailyStatSerializer,
    TaskSerializer,
)


class TodayDashboardView(APIView):
    """
    GET /api/it-ops/today/

    A single snapshot of today's IT workload:
      - tasks due today or overdue, not yet done
      - periodic processes that are due today or overdue
      - department requests still open (pending or in progress)
      - the most recently recorded room occupancy stat
    """

    permission_classes = [IsITStaff]

    def get(self, request):
        now = timezone.localtime()
        end_of_today = now.replace(hour=23, minute=59, second=59, microsecond=999999)

        tasks = (
            Task.objects.filter(due_date__isnull=False, due_date__lte=end_of_today)
            .exclude(status=Task.Status.DONE)
            .order_by("due_date")
        )

        processes = (
            Process.objects.filter(
                next_due_at__isnull=False, next_due_at__lte=end_of_today
            )
            .exclude(status=Process.Status.ARCHIVED)
            .order_by("next_due_at")
        )

        open_requests = DepartmentRequest.objects.filter(
            status__in=[
                DepartmentRequest.Status.PENDING,
                DepartmentRequest.Status.IN_PROGRESS,
            ]
        ).order_by("-priority", "created_at")

        latest_room_stat = RoomDailyStat.objects.order_by("-date").first()

        return Response(
            {
                "date": now.date(),
                "tasks_due_or_overdue": TaskSerializer(tasks, many=True).data,
                "processes_due_or_overdue": ProcessSerializer(
                    processes, many=True
                ).data,
                "open_department_requests": DepartmentRequestSerializer(
                    open_requests, many=True
                ).data,
                "latest_room_stat": (
                    RoomDailyStatSerializer(latest_room_stat).data
                    if latest_room_stat
                    else None
                ),
            }
        )
