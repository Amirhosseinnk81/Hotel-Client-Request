"""
URL configuration for config project.

API routes are versioned under /api/v1/ (see section 17 of the spec).
Individual apps will add their own URL modules under this prefix as they
are built (accounts in Phase 4, tickets in Phase 9, etc.).
"""
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)

admin.site.site_header = "Hotel Client Request Platform Admin"
admin.site.site_title = "Hotel Client Request Platform"
admin.site.index_title = "Administration"

urlpatterns = [
    path("admin/", admin.site.urls),

    path("api/v1/", include("apps.core.urls")),
    path("api/v1/", include("apps.accounts.urls")),
    path("api/v1/", include("apps.guests.urls")),
    path("api/v1/", include("apps.departments.urls")),
    path("api/v1/", include("apps.rooms.urls")),
    path("api/v1/", include("apps.tickets.urls")),

    path(
        "api/schema/",
        SpectacularAPIView.as_view(),
        name="schema",
    ),

    path(
        "api/docs/",
        SpectacularSwaggerView.as_view(url_name="schema"),
        name="swagger-ui",
    ),

    path(
        "api/redoc/",
        SpectacularRedocView.as_view(url_name="schema"),
        name="redoc",
    ),
]

# Local-disk media (Stage 2.8 ticket attachments) — Django only serves
# this itself in DEBUG; a real deployment fronts MEDIA_ROOT with nginx or
# similar, which is out of scope until the production deployment stage.
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)