from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import (
    DepartmentRequestViewSet,
    GoalViewSet,
    ProcessViewSet,
    ProjectViewSet,
    RoomDailyStatViewSet,
    TaskViewSet,
    TodayDashboardView,
)

app_name = "it_ops"

# Mounted at /api/v1/it-ops/ (config/urls.py), like every other API route.
# DefaultRouter's API-root view is left out: the project has no browsable
# API roots elsewhere and it would add an unauthenticated-looking entry.
router = DefaultRouter(trailing_slash=True)
router.include_root_view = False
router.register("processes", ProcessViewSet, basename="process")
router.register("projects", ProjectViewSet, basename="project")
router.register("department-requests", DepartmentRequestViewSet, basename="department-request")
router.register("goals", GoalViewSet, basename="goal")
router.register("tasks", TaskViewSet, basename="task")
router.register("room-stats", RoomDailyStatViewSet, basename="room-stat")

urlpatterns = [
    path("today/", TodayDashboardView.as_view(), name="today-dashboard"),
] + router.urls
