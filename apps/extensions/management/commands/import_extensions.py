from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from apps.extensions.exports import read_rows
from apps.extensions.services import import_rows


class Command(BaseCommand):
    """
    Load the hotel's existing extension list — the `hotel_extensions.xlsx`
    the Flask app used, or any file with the same columns.

    Dry run by default is deliberate: this is how the hotel's whole phone
    directory arrives, and the Flask app showed a preview before writing.
    Nothing is saved until `--confirm`.
    """

    help = (
        "Import the phone directory from a .xlsx or .csv file with the columns "
        "extension, title, person_name, department, location, email, mobile, notes, status.\n\n"
        "  python manage.py import_extensions hotel_extensions.xlsx            # preview only\n"
        "  python manage.py import_extensions hotel_extensions.xlsx --confirm  # actually import"
    )

    def add_arguments(self, parser):
        parser.add_argument("path", help="The .xlsx or .csv file to read.")
        parser.add_argument(
            "--confirm",
            action="store_true",
            help="Actually write. Without it this only reports what would happen.",
        )

    def handle(self, *args, **options):
        path = Path(options["path"])
        if not path.exists():
            raise CommandError(f"File not found: {path}")

        try:
            rows = read_rows(path)
        except ValueError as exc:
            raise CommandError(str(exc)) from exc

        if not rows:
            self.stdout.write(self.style.WARNING("The file has no data rows."))
            return

        commit = options["confirm"]
        report = import_rows(rows, commit=commit)

        self.stdout.write(f"  rows read:              {report.total}")
        self.stdout.write(f"  new numbers:            {report.created}")
        self.stdout.write(f"  existing to update:     {report.updated}")
        if report.restored:
            self.stdout.write(f"  brought back from bin:  {report.restored}")
        if report.duplicates_in_file:
            self.stdout.write(f"  repeated in the file:   {report.duplicates_in_file}")
        if report.skipped:
            self.stdout.write(self.style.WARNING(f"  skipped (unusable):     {report.skipped}"))
            for problem in report.problems[:10]:
                self.stdout.write(f"      {problem}")
            if len(report.problems) > 10:
                self.stdout.write(f"      … and {len(report.problems) - 10} more")
        if report.departments_created:
            label = "created" if commit else "would be created"
            self.stdout.write(f"  departments {label}: {', '.join(report.departments_created)}")

        if commit:
            self.stdout.write(self.style.SUCCESS(f"Imported {report.valid} extension(s)."))
        else:
            self.stdout.write(
                self.style.WARNING(
                    f"Nothing was saved. {report.valid} row(s) would be imported — "
                    "add --confirm to go ahead."
                )
            )
