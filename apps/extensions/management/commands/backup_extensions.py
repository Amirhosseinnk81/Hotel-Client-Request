from django.core.management.base import BaseCommand

from apps.extensions.services import backup_dir, backup_extensions


class Command(BaseCommand):
    """
    The same dated backup as the button in Django Admin, from the
    command line — so it can also go in Windows Task Scheduler and run
    itself every night.
    """

    help = (
        "Write the whole phone directory to a dated .xlsx in "
        "EXTENSIONS_BACKUP_DIR (default <repo>/backups/extensions).\n\n"
        "  python manage.py backup_extensions"
    )

    def handle(self, *args, **options):
        path = backup_extensions()
        self.stdout.write(self.style.SUCCESS(f"Backup written: {path}"))
        self.stdout.write(f"  directory: {backup_dir()}")
