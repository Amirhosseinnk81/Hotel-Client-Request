"""
URL configuration for config project.

API routes are versioned under /api/v1/ (see section 17 of the spec).
Individual apps will add their own URL modules under this prefix as they
are built (accounts in Phase 4, tickets in Phase 9, etc.).
"""
from django.contrib import admin
from django.urls import include, path

admin.site.site_header = "Hotel Client Request Platform Admin"
admin.site.site_title = "Hotel Client Request Platform"
admin.site.index_title = "Administration"

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/v1/", include("apps.core.urls")),
    path("api/v1/", include("apps.accounts.urls")),
]

