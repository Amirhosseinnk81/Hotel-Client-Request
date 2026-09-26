"""
Persian labels and digits for ticket data the server renders itself.

The panel and the guest portal take their labels from
`frontend/src/lib/ticket-labels.ts`. Everything rendered server-side —
the ticket PDF and the in-room TV page (apps/iptv) — shares these, so
the same status can't end up with three different Persian words.
"""

PERSIAN_DIGITS = str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹")

STATUS_LABELS_FA = {
    "OPEN": "باز",
    "IN_PROGRESS": "در حال انجام",
    "RESOLVED": "حل‌شده",
    "CANCELLED": "لغوشده",
}

PRIORITY_LABELS_FA = {
    "LOW": "کم",
    "NORMAL": "عادی",
    "HIGH": "بالا",
    "URGENT": "فوری",
}


def fa_digits(text) -> str:
    return str(text).translate(PERSIAN_DIGITS)
