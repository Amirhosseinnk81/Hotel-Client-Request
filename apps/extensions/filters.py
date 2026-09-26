"""
Searching the directory. The filters are the Flask app's, kept
deliberately: `q` across number/title/person/location/department for the
one box people actually use, plus a narrow filter per column for when
that is too blunt.

One FilterSet serves the list and both exports, so «خروجی» always
matches whatever is on screen — the same reason the Flask version
shared `build_filtered_query`.
"""

import django_filters as filters
from django.db.models import Q

from .models import Extension

STATUS_CHOICES = (("active", "Active"), ("inactive", "Inactive"))

ORDERING_FIELDS = (
    ("extension", "extension"),
    ("title", "title"),
    ("department__name", "department"),
    ("location", "location"),
    ("created_at", "created"),
    ("updated_at", "updated"),
)


class ExtensionFilter(filters.FilterSet):
    q = filters.CharFilter(method="filter_q", label="Search number, title, person, location or department")
    ext = filters.CharFilter(field_name="extension", lookup_expr="icontains")
    person = filters.CharFilter(field_name="person_name", lookup_expr="icontains")
    title_q = filters.CharFilter(field_name="title", lookup_expr="icontains")
    location_q = filters.CharFilter(field_name="location", lookup_expr="icontains")
    status = filters.ChoiceFilter(choices=STATUS_CHOICES, method="filter_status")
    ordering = filters.OrderingFilter(fields=ORDERING_FIELDS)

    class Meta:
        model = Extension
        fields = ("department", "is_active")

    def filter_q(self, queryset, name, value):
        value = value.strip()
        if not value:
            return queryset
        return queryset.filter(
            Q(extension__icontains=value)
            | Q(title__icontains=value)
            | Q(person_name__icontains=value)
            | Q(location__icontains=value)
            | Q(department__name__icontains=value)
        )

    def filter_status(self, queryset, name, value):
        return queryset.filter(is_active=value == "active")
