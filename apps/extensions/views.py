"""
The staff phone directory over HTTP.

Generics, not a ViewSet — the project's default; `it_ops` is the one
deliberate exception (see CLAUDE.md).

Staff read, admins change (`IsStaffReadAdminWrite`). Guests are
authenticated users on this platform, so "any logged-in user" would have
handed them a list of staff mobiles; the panel page is for operators and
the managing is done in Django Admin, as with rooms, departments and
categories.

Both exports run the list's own filters, so «خروجی» always matches what
the person is looking at.
"""

from django.http import HttpResponse
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import generics, status
from rest_framework.response import Response

from apps.core.permissions import IsStaffReadAdminWrite

from .exports import to_csv, to_xlsx
from .filters import ExtensionFilter
from .models import Extension
from .pdf import build_extensions_pdf
from .serializers import ExtensionSerializer


def _base_queryset():
    return Extension.objects.alive().select_related("department")


class ExtensionListCreateView(generics.ListCreateAPIView):
    """
    GET: the directory, searchable with `q` or per column.
    POST: a new number (admins only).
    """

    serializer_class = ExtensionSerializer
    permission_classes = [IsStaffReadAdminWrite]
    filterset_class = ExtensionFilter
    queryset = _base_queryset()

    def get_queryset(self):
        return _base_queryset()


class ExtensionDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    DELETE is a soft delete: the row goes to the trash, where Django
    Admin can restore it. A phone directory is exactly the sort of list
    somebody clears by accident.
    """

    serializer_class = ExtensionSerializer
    permission_classes = [IsStaffReadAdminWrite]
    queryset = _base_queryset()

    def get_queryset(self):
        return _base_queryset()

    def perform_destroy(self, instance):
        instance.soft_delete()


class _ExportView(generics.GenericAPIView):
    """Shared plumbing: same permission, same filters as the list."""

    serializer_class = ExtensionSerializer
    permission_classes = [IsStaffReadAdminWrite]
    filterset_class = ExtensionFilter
    queryset = _base_queryset()

    def get_queryset(self):
        return _base_queryset()

    def filtered(self, request):
        return self.filter_queryset(self.get_queryset())

    @staticmethod
    def attachment(content: bytes, filename: str, content_type: str) -> HttpResponse:
        response = HttpResponse(content, content_type=content_type)
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response


@extend_schema(
    responses={(200, "application/pdf"): bytes},
    parameters=[OpenApiParameter("q", str, description="Same search as the list endpoint.")],
)
class ExtensionPdfExportView(_ExportView):
    """
    The printed phone list: landscape A4, two columns, grouped by
    department — `application/pdf`, not JSON.
    """

    def get(self, request, *args, **kwargs):
        rows = list(self.filtered(request).order_by("department__name", "extension"))
        return self.attachment(build_extensions_pdf(rows), "extensions.pdf", "application/pdf")


@extend_schema(responses={(200, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"): bytes})
class ExtensionExcelExportView(_ExportView):
    """
    The same columns the importer reads, so an export can be edited and
    imported straight back.
    """

    def get(self, request, *args, **kwargs):
        rows = list(self.filtered(request))
        return self.attachment(
            to_xlsx(rows),
            "extensions.xlsx",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )


@extend_schema(responses={(200, "text/csv"): bytes})
class ExtensionCsvExportView(_ExportView):
    def get(self, request, *args, **kwargs):
        rows = list(self.filtered(request))
        return self.attachment(to_csv(rows), "extensions.csv", "text/csv; charset=utf-8")


class ExtensionRestoreView(generics.GenericAPIView):
    """Bring one number back from the trash (admins only)."""

    serializer_class = ExtensionSerializer
    permission_classes = [IsStaffReadAdminWrite]
    queryset = Extension.objects.deleted()
    http_method_names = ["post"]

    def get_queryset(self):
        return Extension.objects.deleted().select_related("department")

    def post(self, request, *args, **kwargs):
        # POST, so IsStaffReadAdminWrite requires an admin.
        item = self.get_object()
        item.restore()
        return Response(self.get_serializer(item).data, status=status.HTTP_200_OK)
