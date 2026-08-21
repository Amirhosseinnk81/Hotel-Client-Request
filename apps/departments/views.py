from rest_framework import generics

from apps.core.permissions import IsAdminRole

from .models import Department
from .serializers import DepartmentSerializer


class DepartmentListCreateView(generics.ListCreateAPIView):
    """
    GET  /api/v1/departments/  — any authenticated user (guest/operator/admin) can browse.
    POST /api/v1/departments/  — admins only.
    """

    queryset = Department.objects.all()
    serializer_class = DepartmentSerializer
    permission_classes = [IsAdminRole]


class DepartmentDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    GET/PATCH/PUT — read for anyone authenticated, write for admins only.
    DELETE is admin-only too (blocked at the DB level anyway while
    tickets/operators reference the department, since department FKs use PROTECT).
    """

    queryset = Department.objects.all()
    serializer_class = DepartmentSerializer
    permission_classes = [IsAdminRole]