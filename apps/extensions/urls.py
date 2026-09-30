from django.urls import path

from .views import (
    ExtensionCsvExportView,
    ExtensionDetailView,
    ExtensionExcelExportView,
    ExtensionListCreateView,
    ExtensionPdfExportView,
    ExtensionRestoreView,
    ExtensionVersionView,
)

app_name = "extensions"

urlpatterns = [
    path("extensions/", ExtensionListCreateView.as_view(), name="list"),
    # Before <pk>/ so "export" is never read as an id.
    path("extensions/export/pdf/", ExtensionPdfExportView.as_view(), name="export-pdf"),
    path("extensions/export/excel/", ExtensionExcelExportView.as_view(), name="export-excel"),
    path("extensions/export/csv/", ExtensionCsvExportView.as_view(), name="export-csv"),
    path("extensions/version/", ExtensionVersionView.as_view(), name="version"),
    path("extensions/<int:pk>/", ExtensionDetailView.as_view(), name="detail"),
    path("extensions/<int:pk>/restore/", ExtensionRestoreView.as_view(), name="restore"),
]
