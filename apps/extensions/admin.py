from django import forms
from django.contrib import admin, messages
from django.shortcuts import redirect, render
from django.urls import path, reverse
from django.utils import timezone
from django.utils.html import format_html

from .exports import COLUMNS, read_rows
from .models import Extension, ExtensionActivity
from .services import backup_extensions, import_rows, label_for, log_activity

# Where a previewed file waits between "check it" and "do it". The rows
# are small (a hotel's phone list), already parsed, and scoped to the
# admin's own session — no temp files to clean up, unlike the Flask
# version's token-and-tmpdir dance.
IMPORT_SESSION_KEY = "extensions_import_rows"
MAX_PREVIEW_ROWS = 5000


class ImportForm(forms.Form):
    file = forms.FileField(
        label="فایل اکسل یا CSV",
        help_text=f"ستون‌ها: {', '.join(COLUMNS)}",
    )


@admin.register(Extension)
class ExtensionAdmin(admin.ModelAdmin):
    """
    Where the hotel manages the phone directory. The panel page is
    read-only on purpose — reference data (rooms, departments,
    categories) is managed here, and this is reference data too.

    Deleting from the list marks rows as deleted rather than removing
    them; "Delete permanently" is the only way to actually lose a row.

    Two buttons above the list carry over from the Flask app: importing
    a spreadsheet (with a preview first) and taking a dated backup.
    """

    change_list_template = "admin/extensions/extension/change_list.html"
    list_display = ("extension", "title", "person_name", "department", "location", "is_active", "is_deleted")
    list_filter = ("is_active", "is_deleted", "department")
    search_fields = ("extension", "title", "person_name", "location", "mobile", "email", "notes")
    list_select_related = ("department",)
    readonly_fields = ("created_at", "updated_at", "deleted_at")
    actions = ["activate", "deactivate", "send_to_trash", "restore", "delete_permanently"]
    list_per_page = 50

    # -- who did what ----------------------------------------------------

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        log_activity(
            request.user,
            ExtensionActivity.Action.UPDATED if change else ExtensionActivity.Action.CREATED,
            label_for(obj),
            details=", ".join(sorted(form.changed_data)) if change else "",
        )

    def delete_model(self, request, obj):
        label = label_for(obj)
        super().delete_model(request, obj)
        log_activity(request.user, ExtensionActivity.Action.DELETED, label)

    # -- actions ---------------------------------------------------------

    @admin.action(description="Mark as in use")
    def activate(self, request, queryset):
        count = queryset.update(is_active=True)
        log_activity(request.user, ExtensionActivity.Action.UPDATED, f"{count} extension(s)", "marked in use")
        self.message_user(request, f"{count} marked as in use.", messages.SUCCESS)

    @admin.action(description="Mark as out of use")
    def deactivate(self, request, queryset):
        count = queryset.update(is_active=False)
        log_activity(request.user, ExtensionActivity.Action.UPDATED, f"{count} extension(s)", "marked out of use")
        self.message_user(request, f"{count} marked as out of use.", messages.SUCCESS)

    @admin.action(description="Move to the trash (restorable)")
    def send_to_trash(self, request, queryset):
        count = queryset.filter(is_deleted=False).update(is_deleted=True, deleted_at=timezone.now())
        log_activity(request.user, ExtensionActivity.Action.TRASHED, f"{count} extension(s)")
        self.message_user(request, f"{count} moved to the trash.", messages.SUCCESS)

    @admin.action(description="Restore from the trash")
    def restore(self, request, queryset):
        count = queryset.filter(is_deleted=True).update(is_deleted=False, deleted_at=None)
        log_activity(request.user, ExtensionActivity.Action.RESTORED, f"{count} extension(s)")
        self.message_user(request, f"{count} restored.", messages.SUCCESS)

    @admin.action(description="Delete permanently (cannot be undone)")
    def delete_permanently(self, request, queryset):
        count, _ = queryset.delete()
        log_activity(request.user, ExtensionActivity.Action.DELETED, f"{count} extension(s)")
        self.message_user(request, f"{count} deleted for good.", messages.WARNING)

    # -- import and backup ------------------------------------------------

    def get_urls(self):
        own = [
            path(
                "import/",
                self.admin_site.admin_view(self.import_view),
                name="extensions_extension_import",
            ),
            path(
                "backup/",
                self.admin_site.admin_view(self.backup_view),
                name="extensions_extension_backup",
            ),
        ]
        return own + super().get_urls()

    def import_view(self, request):
        """
        Upload, look at what it would do, then confirm — the Flask app's
        two-step import, through the same `import_rows` the command line
        uses, so there is one importer and not two.
        """
        context = {
            **self.admin_site.each_context(request),
            "title": "ورود فهرست داخلی‌ها",
            "opts": self.model._meta,
            "form": ImportForm(),
            "report": None,
        }

        if request.method == "POST" and "confirm" in request.POST:
            rows = request.session.pop(IMPORT_SESSION_KEY, None)
            if not rows:
                self.message_user(request, "پیش‌نمایشی برای تأیید پیدا نشد؛ دوباره فایل را انتخاب کنید.", messages.ERROR)
                return redirect("admin:extensions_extension_import")
            report = import_rows(rows, commit=True, actor=request.user)
            self.message_user(request, f"{report.valid} داخلی وارد یا به‌روزرسانی شد.", messages.SUCCESS)
            return redirect("admin:extensions_extension_changelist")

        if request.method == "POST":
            form = ImportForm(request.POST, request.FILES)
            context["form"] = form
            if form.is_valid():
                upload = form.cleaned_data["file"]
                try:
                    rows = _rows_from_upload(upload)
                except ValueError as exc:
                    self.message_user(request, str(exc), messages.ERROR)
                    return render(request, "admin/extensions/import.html", context)

                if len(rows) > MAX_PREVIEW_ROWS:
                    self.message_user(
                        request,
                        f"فایل بیش از {MAX_PREVIEW_ROWS} ردیف دارد؛ از دستور import_extensions استفاده کنید.",
                        messages.ERROR,
                    )
                    return render(request, "admin/extensions/import.html", context)

                # commit=False runs the real importer and rolls back, so
                # the preview can never disagree with what confirming does.
                context["report"] = import_rows(rows, commit=False)
                request.session[IMPORT_SESSION_KEY] = rows

        return render(request, "admin/extensions/import.html", context)

    def backup_view(self, request):
        """A dated .xlsx of the whole directory, written to EXTENSIONS_BACKUP_DIR."""
        try:
            path = backup_extensions(actor=request.user)
        except OSError as exc:
            self.message_user(request, f"بکاپ گرفته نشد: {exc}", messages.ERROR)
        else:
            self.message_user(request, f"بکاپ ذخیره شد: {path}", messages.SUCCESS)
        return redirect("admin:extensions_extension_changelist")


def _rows_from_upload(upload):
    """
    read_rows() works on a path; an upload is a stream. Spool it to a
    temp file, parse, and delete it right away — nothing of the guest's
    hotel data is left lying around.
    """
    import os
    import tempfile

    suffix = os.path.splitext(upload.name)[1].lower()
    if suffix not in (".csv", ".xlsx"):
        raise ValueError("فقط فایل CSV یا XLSX پذیرفته می‌شود.")

    handle = tempfile.NamedTemporaryFile("wb", suffix=suffix, delete=False)
    try:
        for chunk in upload.chunks():
            handle.write(chunk)
        handle.close()
        return read_rows(handle.name)
    finally:
        try:
            os.unlink(handle.name)
        except OSError:
            pass


@admin.register(ExtensionActivity)
class ExtensionActivityAdmin(admin.ModelAdmin):
    """
    The directory's history — who added, changed, trashed, imported or
    backed up, and when. Read-only: it is a record, not a workspace.
    """

    list_display = ("created_at", "actor_display", "action", "label", "details")
    list_filter = ("action", "created_at")
    search_fields = ("actor", "label", "details")
    date_hierarchy = "created_at"
    list_per_page = 100

    @admin.display(description="Actor", ordering="actor")
    def actor_display(self, obj):
        return obj.actor or format_html("<em>system</em>")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
