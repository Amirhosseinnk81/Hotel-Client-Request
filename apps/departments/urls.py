from django.urls import path

from .views import DepartmentDetailView, DepartmentListCreateView

app_name = "departments"

urlpatterns = [
    path("departments/", DepartmentListCreateView.as_view(), name="department-list"),
    path("departments/<int:pk>/", DepartmentDetailView.as_view(), name="department-detail"),
]
