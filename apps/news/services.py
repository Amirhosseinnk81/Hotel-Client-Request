"""
Who sees which announcement — one rule, read by both endpoints and by
the room TV.

Kept out of the views for the same reason as apps/chat/services.py: the
guest portal, the operator panel and `apps/iptv` all ask this question,
and three copies of the answer would eventually disagree about whether a
staff briefing is guest-visible.
"""

from .models import NewsItem


def guest_news(now=None):
    """Everything published for guests — the portal and the room TV."""
    return (
        NewsItem.objects.published(now)
        .for_audience(NewsItem.Audience.GUEST)
        .order_by("-is_pinned", "-publish_at", "-id")
    )


def staff_news(user, now=None):
    """
    Everything published for staff, plus the items aimed at their own
    department.

    A department-scoped item is for that team only; an item with no
    department is for the whole hotel. An admin has no department, so
    they see the hotel-wide ones — which is the right side to err on for
    management, since they can read every item in Django Admin anyway.
    """
    queryset = NewsItem.objects.published(now).for_audience(NewsItem.Audience.STAFF)
    department_id = getattr(user, "department_id", None)
    if department_id:
        queryset = queryset.filter(department__isnull=True) | queryset.filter(
            department_id=department_id
        )
    else:
        queryset = queryset.filter(department__isnull=True)
    return queryset.distinct().order_by("-is_pinned", "-publish_at", "-id")
