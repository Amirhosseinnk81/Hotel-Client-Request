"""The staff phone directory, ported from the Flask app Hotel-extensions."""

import csv
import tempfile
from io import StringIO
from pathlib import Path

from django.core.management import CommandError, call_command
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import User
from apps.departments.models import Department
from apps.guests.models import Guest
from apps.rooms.models import Room

from .exports import COLUMNS, read_rows, to_csv, to_xlsx
from .models import Extension
from .pdf import build_extensions_pdf
from .services import ascii_digits, import_rows


class ExtensionTestData:
    @classmethod
    def setUpTestData(cls):
        cls.reception = Department.objects.create(
            name="پذیرش", code="RECEPTION_X", working_hours="۲۴ ساعته"
        )
        cls.housekeeping = Department.objects.create(name="خانه‌داری", code="HK_X")

        cls.admin = User.objects.create_user(username="admin_x", password="x", role=User.Role.ADMIN)
        cls.operator = User.objects.create_user(
            username="op_x", password="x", role=User.Role.OPERATOR, department=cls.housekeeping
        )
        room = Room.objects.create(number="701", status=Room.Status.OCCUPIED)
        guest_user = User.objects.create(username="guest_x", role=User.Role.GUEST)
        guest_user.set_unusable_password()
        guest_user.save()
        cls.guest_user = guest_user
        Guest.objects.create(user=guest_user, full_name="مهمان", national_id="0090090090", room=room)

        cls.front_desk = Extension.objects.create(
            extension="100", title="پذیرش", person_name="رضا مرادی", department=cls.reception, location="لابی"
        )
        cls.laundry = Extension.objects.create(
            extension="210", title="لباسشویی", department=cls.housekeeping, location="طبقه منفی یک"
        )
        cls.old_fax = Extension.objects.create(extension="999", title="فکس قدیمی", is_active=False)


class ExtensionApiTests(ExtensionTestData, APITestCase):
    def test_staff_can_look_up_the_directory(self):
        self.client.force_authenticate(self.operator)

        response = self.client.get(reverse("extensions:list"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        numbers = [row["extension"] for row in response.data["results"]]
        self.assertEqual(numbers, ["100", "210", "999"])  # ordered by number

    def test_a_row_carries_its_department_s_name_and_hours(self):
        self.client.force_authenticate(self.operator)

        row = self.client.get(reverse("extensions:list"), {"ext": "100"}).data["results"][0]

        self.assertEqual(row["department_name"], "پذیرش")
        self.assertEqual(row["department_working_hours"], "۲۴ ساعته")

    def test_a_guest_cannot_read_the_staff_directory(self):
        # It carries staff names, mobiles and locations.
        self.client.force_authenticate(self.guest_user)

        self.assertEqual(self.client.get(reverse("extensions:list")).status_code, 403)

    def test_an_anonymous_visitor_cannot_read_it_either(self):
        self.assertEqual(self.client.get(reverse("extensions:list")).status_code, 401)

    def test_one_search_box_covers_number_title_person_location_and_department(self):
        self.client.force_authenticate(self.operator)
        url = reverse("extensions:list")

        for term, expected in (
            ("210", ["210"]),
            ("لباسشویی", ["210"]),
            ("مرادی", ["100"]),
            ("لابی", ["100"]),
            ("خانه‌داری", ["210"]),
        ):
            with self.subTest(term=term):
                found = [row["extension"] for row in self.client.get(url, {"q": term}).data["results"]]
                self.assertEqual(found, expected)

    def test_the_status_filter_separates_numbers_in_and_out_of_use(self):
        self.client.force_authenticate(self.operator)
        url = reverse("extensions:list")

        active = self.client.get(url, {"status": "active"}).data["results"]
        inactive = self.client.get(url, {"status": "inactive"}).data["results"]

        self.assertEqual(sorted(row["extension"] for row in active), ["100", "210"])
        self.assertEqual([row["extension"] for row in inactive], ["999"])

    def test_results_can_be_sorted_by_department(self):
        self.client.force_authenticate(self.operator)

        response = self.client.get(reverse("extensions:list"), {"ordering": "-department"})

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_an_operator_cannot_change_the_directory(self):
        self.client.force_authenticate(self.operator)

        created = self.client.post(reverse("extensions:list"), {"extension": "300", "title": "انبار"})
        edited = self.client.patch(reverse("extensions:detail", args=[self.laundry.pk]), {"title": "x"})
        deleted = self.client.delete(reverse("extensions:detail", args=[self.laundry.pk]))

        for response in (created, edited, deleted):
            self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_an_admin_manages_the_directory(self):
        self.client.force_authenticate(self.admin)

        created = self.client.post(
            reverse("extensions:list"),
            {"extension": "300", "title": "انبار", "department": self.housekeeping.pk},
        )
        edited = self.client.patch(
            reverse("extensions:detail", args=[self.laundry.pk]), {"location": "طبقه همکف"}
        )

        self.assertEqual(created.status_code, status.HTTP_201_CREATED)
        self.assertEqual(edited.status_code, status.HTTP_200_OK)
        self.laundry.refresh_from_db()
        self.assertEqual(self.laundry.location, "طبقه همکف")

    def test_two_numbers_cannot_share_one_extension(self):
        self.client.force_authenticate(self.admin)

        response = self.client.post(reverse("extensions:list"), {"extension": "100", "title": "دیگری"})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_deleting_moves_a_number_to_the_trash_instead_of_losing_it(self):
        self.client.force_authenticate(self.admin)

        response = self.client.delete(reverse("extensions:detail", args=[self.laundry.pk]))

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.laundry.refresh_from_db()
        self.assertTrue(self.laundry.is_deleted)
        self.assertIsNotNone(self.laundry.deleted_at)
        # Gone from the directory, still in the database.
        listed = self.client.get(reverse("extensions:list")).data["results"]
        self.assertNotIn("210", [row["extension"] for row in listed])

    def test_a_deleted_number_can_be_restored(self):
        self.laundry.soft_delete()
        self.client.force_authenticate(self.admin)

        response = self.client.post(reverse("extensions:restore", args=[self.laundry.pk]))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.laundry.refresh_from_db()
        self.assertFalse(self.laundry.is_deleted)

    def test_an_operator_cannot_restore(self):
        self.laundry.soft_delete()
        self.client.force_authenticate(self.operator)

        self.assertEqual(
            self.client.post(reverse("extensions:restore", args=[self.laundry.pk])).status_code, 403
        )


class ExtensionExportTests(ExtensionTestData, APITestCase):
    def test_the_pdf_is_a_pdf_not_json(self):
        self.client.force_authenticate(self.operator)

        response = self.client.get(reverse("extensions:export-pdf"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response["Content-Type"], "application/pdf")
        self.assertTrue(response.content.startswith(b"%PDF-"))
        self.assertIn("attachment", response["Content-Disposition"])

    def test_an_export_matches_the_search_that_produced_it(self):
        self.client.force_authenticate(self.operator)

        response = self.client.get(reverse("extensions:export-csv"), {"q": "لباسشویی"})

        body = response.content.decode("utf-8-sig")
        self.assertIn("210", body)
        self.assertNotIn("100", body)

    def test_excel_and_csv_carry_the_columns_the_importer_reads(self):
        self.client.force_authenticate(self.operator)

        excel = self.client.get(reverse("extensions:export-excel"))
        csv_response = self.client.get(reverse("extensions:export-csv"))

        self.assertIn("spreadsheetml", excel["Content-Type"])
        self.assertTrue(excel.content.startswith(b"PK"))  # xlsx is a zip
        header = csv_response.content.decode("utf-8-sig").splitlines()[0]
        self.assertEqual(header.strip().split(","), list(COLUMNS))

    def test_a_guest_cannot_download_the_directory(self):
        self.client.force_authenticate(self.guest_user)

        for name in ("extensions:export-pdf", "extensions:export-csv", "extensions:export-excel"):
            with self.subTest(name=name):
                self.assertEqual(self.client.get(reverse(name)).status_code, 403)

    def test_the_pdf_survives_an_empty_directory(self):
        content = build_extensions_pdf([])

        self.assertTrue(content.startswith(b"%PDF-"))

    def test_an_export_can_be_imported_straight_back(self):
        original = list(Extension.objects.alive())
        data = to_csv(original)
        Extension.objects.all().delete()

        with tempfile.NamedTemporaryFile("wb", suffix=".csv", delete=False) as handle:
            handle.write(data)
            path = handle.name
        report = import_rows(read_rows(path), commit=True)

        self.assertEqual(report.created, 3)
        self.assertEqual(Extension.objects.get(extension="100").person_name, "رضا مرادی")
        self.assertFalse(Extension.objects.get(extension="999").is_active)


class ExtensionImportTests(ExtensionTestData, TestCase):
    def write_csv(self, rows, header=None):
        header = header or list(COLUMNS)
        with tempfile.NamedTemporaryFile("w", suffix=".csv", delete=False, encoding="utf-8-sig", newline="") as handle:
            writer = csv.writer(handle)
            writer.writerow(header)
            writer.writerows(rows)
            return handle.name

    def test_a_preview_changes_nothing(self):
        path = self.write_csv([["400", "آبدارخانه", "", "پذیرش", "", "", "", "", "فعال"]])

        report = import_rows(read_rows(path), commit=False)

        self.assertEqual(report.created, 1)
        self.assertFalse(Extension.objects.filter(extension="400").exists())

    def test_an_existing_number_is_updated_not_duplicated(self):
        path = self.write_csv([["100", "پذیرش شب", "مریم قاسمی", "پذیرش", "لابی", "", "", "", "فعال"]])

        report = import_rows(read_rows(path), commit=True)

        self.assertEqual((report.created, report.updated), (0, 1))
        self.assertEqual(Extension.objects.filter(extension="100").count(), 1)
        self.front_desk.refresh_from_db()
        self.assertEqual(self.front_desk.title, "پذیرش شب")
        self.assertEqual(self.front_desk.person_name, "مریم قاسمی")

    def test_a_department_the_hotel_does_not_have_yet_is_created(self):
        path = self.write_csv([["500", "استخر", "", "تأسیسات", "", "", "", "", "فعال"]])

        report = import_rows(read_rows(path), commit=True)

        self.assertEqual(report.departments_created, ["تأسیسات"])
        department = Department.objects.get(name="تأسیسات")
        self.assertTrue(department.code)  # the platform requires a unique code
        self.assertEqual(Extension.objects.get(extension="500").department, department)

    def test_a_row_without_a_number_or_a_title_is_reported_not_guessed(self):
        path = self.write_csv(
            [
                ["", "بدون شماره", "", "", "", "", "", "", "فعال"],
                ["600", "", "", "", "", "", "", "", "فعال"],
                ["601", "درست", "", "", "", "", "", "", "فعال"],
            ]
        )

        report = import_rows(read_rows(path), commit=True)

        self.assertEqual(report.skipped, 2)
        self.assertEqual(report.created, 1)
        self.assertEqual(len(report.problems), 2)

    def test_persian_digits_are_the_same_number_as_ascii(self):
        path = self.write_csv([["۱۰۰", "پذیرش", "", "", "", "", "", "", "فعال"]])

        report = import_rows(read_rows(path), commit=True)

        self.assertEqual((report.created, report.updated), (0, 1))
        self.assertEqual(ascii_digits("۲۱۰"), "210")

    def test_the_persian_word_for_inactive_is_understood(self):
        path = self.write_csv(
            [
                ["700", "قدیمی", "", "", "", "", "", "", "غیرفعال"],
                ["701", "تازه", "", "", "", "", "", "", "فعال"],
            ]
        )

        import_rows(read_rows(path), commit=True)

        self.assertFalse(Extension.objects.get(extension="700").is_active)
        self.assertTrue(Extension.objects.get(extension="701").is_active)

    def test_a_number_in_the_trash_comes_back_when_the_file_has_it_again(self):
        self.laundry.soft_delete()
        path = self.write_csv([["210", "لباسشویی", "", "خانه‌داری", "", "", "", "", "فعال"]])

        report = import_rows(read_rows(path), commit=True)

        self.assertEqual(report.restored, 1)
        self.laundry.refresh_from_db()
        self.assertFalse(self.laundry.is_deleted)

    def test_the_same_number_twice_in_one_file_is_counted(self):
        path = self.write_csv(
            [["800", "اول", "", "", "", "", "", "", "فعال"], ["800", "دوم", "", "", "", "", "", "", "فعال"]]
        )

        report = import_rows(read_rows(path), commit=True)

        self.assertEqual(report.duplicates_in_file, 1)
        self.assertEqual(Extension.objects.get(extension="800").title, "دوم")  # last wins

    def test_an_xlsx_file_is_read_too(self):
        # The hotel's own list is hotel_extensions.xlsx.
        data = to_xlsx(Extension.objects.alive())
        Extension.objects.all().delete()
        with tempfile.NamedTemporaryFile("wb", suffix=".xlsx", delete=False) as handle:
            handle.write(data)
            path = handle.name

        report = import_rows(read_rows(path), commit=True)

        self.assertEqual(report.created, 3)

    def test_an_unreadable_file_says_so(self):
        with self.assertRaises(ValueError):
            read_rows(Path("directory.txt"))


class ImportCommandTests(ExtensionTestData, TestCase):
    def csv_path(self, rows):
        with tempfile.NamedTemporaryFile("w", suffix=".csv", delete=False, encoding="utf-8-sig", newline="") as handle:
            writer = csv.writer(handle)
            writer.writerow(list(COLUMNS))
            writer.writerows(rows)
            return handle.name

    def test_it_previews_by_default_and_writes_nothing(self):
        path = self.csv_path([["900", "سالن", "", "", "", "", "", "", "فعال"]])
        out = StringIO()

        call_command("import_extensions", path, stdout=out)

        self.assertIn("Nothing was saved", out.getvalue())
        self.assertFalse(Extension.objects.filter(extension="900").exists())

    def test_with_confirm_it_imports(self):
        path = self.csv_path([["900", "سالن", "", "", "", "", "", "", "فعال"]])
        out = StringIO()

        call_command("import_extensions", path, "--confirm", stdout=out)

        self.assertIn("Imported 1", out.getvalue())
        self.assertTrue(Extension.objects.filter(extension="900").exists())

    def test_a_missing_file_is_an_error_not_a_traceback(self):
        with self.assertRaises(CommandError):
            call_command("import_extensions", "nope.xlsx", stdout=StringIO())
