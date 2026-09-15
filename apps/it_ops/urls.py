from django.urls import path
from rest_framework.routers import DefaultRouter

from .dashboard_views import TodayDashboardView
from .views import (
    DepartmentRequestViewSet,
    GoalViewSet,
    ProcessViewSet,
    ProjectViewSet,
    RoomDailyStatViewSet,
    TaskViewSet,
)

router = DefaultRouter()
router.register("processes", ProcessViewSet, basename="process")
router.register("projects", ProjectViewSet, basename="project")
router.register(
    "department-requests", DepartmentRequestViewSet, basename="department-request"
)
router.register("goals", GoalViewSet, basename="goal")
router.register("tasks", TaskViewSet, basename="task")
router.register("room-stats", RoomDailyStatViewSet, basename="room-stat")

urlpatterns = [
    path("today/", TodayDashboardView.as_view(), name="today-dashboard"),
] + router.urls
