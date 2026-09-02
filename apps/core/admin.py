from django.contrib import admin
from django.shortcuts import render
from django.urls import path
from django.utils.translation import gettext_lazy as _

# apps.tickets is safe to import here: admin.py modules are imported by
# Django's admin autodiscovery after the app registry is fully populated,
# well after every app's models are ready.
from apps.tickets.services import compute_admin_stats_summary

# --- Custom "stats" page --------------------------------------------------
# Stage 2.4 frontend deliverable: a lightweight view inside Django Admin
# showing the same numbers as AdminStatsSummaryView (apps/tickets/views.py),
# so an admin doesn't have to read the database by hand. Deliberately reuses
# compute_admin_stats_summary() rather than calling the DRF endpoint over
# HTTP, since Django Admin auth is session-based, not JWT -- no reason to
# round-trip through the API for data that lives in the same process.
#
# Wired in via get_urls()/get_app_list() rather than overriding
# admin/index.html: this project's app search order has django.contrib.admin
# *before* apps.core (see INSTALLED_APPS in config/settings/base.py), so an
# apps/core template named admin/index.html would never be found ahead of
# Django's own -- and even if it were, {% extends "admin/index.html" %} on a
# same-named template recurses infinitely. get_app_list() is the officially
# supported extension point for adding a non-model link to the admin index
# without touching any built-in template.


def stats_summary_view(request):
    data = compute_admin_stats_summary()
    context = {
        **admin.site.each_context(request),
        # English/LTR to match the rest of Django Admin (site_header,
        # every ModelAdmin's list_display/verbose_name) — the
        # Persian/RTL requirement in the Stage-2 spec applies to the
        # Next.js frontend, not this backend-only admin surface.
        "title": _("Stats Summary"),
        "stats": data,
    }
    return render(request, "admin/stats_summary.html", context)


_original_get_urls = admin.site.get_urls
_original_get_app_list = admin.site.get_app_list


def _get_urls():
    custom_urls = [
        path(
            "stats/",
            admin.site.admin_view(stats_summary_view),
            name="stats-summary",
        ),
    ]
    # Custom URLs must come before the originals: admin.site.urls includes
    # a catch-all pattern for app_index/model views that would otherwise
    # shadow "stats/".
    return custom_urls + _original_get_urls()


def _get_app_list(request, *args, **kwargs):
    app_list = _original_get_app_list(request, *args, **kwargs)
    if request.user.is_active and (
        request.user.is_superuser or getattr(request.user, "role", None) == "ADMIN"
    ):
        app_list.insert(
            0,
            {
                "name": _("Reports"),
                "app_label": "stats",
                "app_url": "#",
                "has_module_perms": True,
                "models": [
                    {
                        "name": _("Ticket Stats Summary"),
                        "object_name": "stats_summary",
                        "admin_url": "/admin/stats/",
                        "view_only": True,
                        "perms": {"view": True},
                    }
                ],
            },
        )
    return app_list


admin.site.get_urls = _get_urls
admin.site.get_app_list = _get_app_list
