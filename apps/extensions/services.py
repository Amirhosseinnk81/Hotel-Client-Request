"""
Importing the hotel's extension list.

Non-CRUD logic, so it lives here rather than in a view or a command —
the same rule as apps/tickets/services.py. The command and the tests
both call `import_rows`, and it can report without writing (`commit=
False`), which is how the Flask app's preview-then-confirm screen is
kept: see what the file would do, then do it.

Upsert by extension number, exactly as before: a number already in the
directory is updated rather than duplicated, and one that was in the
trash comes back rather than colliding with a unique constraint.
"""

from dataclasses import dataclass, field
from unicodedata import normalize

from django.db import transaction
from django.utils.text import slugify

from apps.departments.models import Department

from .exports import is_active_value
from .models import Extension

# Persian/Arabic-Indic digits, as they arrive from a hand-typed
# spreadsheet. Extension numbers are matched and stored in ASCII so
# «۳۰۵» and "305" are the same number, not two rows.
_DIGITS = str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789")


def ascii_digits(value) -> str:
    return normalize("NFKC", str(value or "")).translate(_DIGITS).strip()


@dataclass
class ImportReport:
    total: int = 0
    created: int = 0
    updated: int = 0
    skipped: int = 0
    restored: int = 0
    duplicates_in_file: int = 0
    departments_created: list[str] = field(default_factory=list)
    problems: list[str] = field(default_factory=list)

    @property
    def valid(self) -> int:
        return self.created + self.updated


def department_for(name, report, *, commit=True):
    """
    Match a department by name, creating it when the hotel's file names
    one we don't have. The platform's departments need a unique code as
    well as a name, so one is derived from the name (and de-duplicated);
    the hotel can rename it later in Django Admin.
    """
    name = str(name or "").strip()
    if not name:
        return None

    existing = Department.objects.filter(name=name).first()
    if existing is not None:
        return existing

    if name not in report.departments_created:
        report.departments_created.append(name)
    if not commit:
        # Nothing is created during a preview, so every later row naming
        # this department would report it again — hence the check above.
        return None

    base = (slugify(name, allow_unicode=False) or "dept").upper().replace("-", "_")[:40]
    code = base
    suffix = 2
    while Department.objects.filter(code=code).exists():
        code = f"{base[:44]}_{suffix}"
        suffix += 1
    return Department.objects.create(name=name, code=code)


def _value(row, *names):
    for name in names:
        if name in row and str(row[name]).strip():
            return str(row[name]).strip()
    return ""


@transaction.atomic
def import_rows(rows, *, commit=True) -> ImportReport:
    """
    Apply (or, with commit=False, just report on) rows read from the
    hotel's CSV/Excel file. Always rolls back when commit is False, so a
    preview can use the real code path instead of a second, drifting
    copy of the same logic.
    """
    report = ImportReport(total=len(rows))
    seen: set[str] = set()

    for index, row in enumerate(rows, start=2):  # row 1 is the header
        number = ascii_digits(_value(row, "extension", "داخلی", "شماره"))
        title = _value(row, "title", "عنوان")
        if not number or not title:
            report.skipped += 1
            report.problems.append(f"row {index}: needs both an extension number and a title")
            continue
        if number in seen:
            report.duplicates_in_file += 1
        seen.add(number)

        department = department_for(_value(row, "department", "واحد"), report, commit=commit)
        existing = Extension.objects.filter(extension=number).first()

        if existing is None:
            report.created += 1
        else:
            report.updated += 1
            if existing.is_deleted:
                report.restored += 1

        if not commit:
            continue

        item = existing or Extension(extension=number)
        item.title = title
        item.person_name = _value(row, "person_name", "نام", "نام شخص")
        item.department = department
        item.location = _value(row, "location", "محل")
        item.email = _value(row, "email", "ایمیل")
        item.mobile = ascii_digits(_value(row, "mobile", "موبایل", "همراه"))
        item.notes = _value(row, "notes", "یادداشت", "توضیحات")
        item.is_active = is_active_value(_value(row, "status", "وضعیت") or "فعال")
        # A number that was in the trash and turns up in the file again
        # is back in service.
        item.is_deleted = False
        item.deleted_at = None
        item.save()

    if not commit:
        transaction.set_rollback(True)
    return report
