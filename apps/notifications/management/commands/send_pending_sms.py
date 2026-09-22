from django.core.management.base import BaseCommand

from apps.notifications.services import send_pending_sms


class Command(BaseCommand):
    help = (
        "Send the SMS messages waiting in the outbox (Stage 3.1) and retry "
        "failed ones with backoff. Meant to run every minute from Windows "
        "Task Scheduler: python manage.py send_pending_sms"
    )

    def add_arguments(self, parser):
        parser.add_argument("--limit", type=int, default=100, help="Most messages per run.")

    def handle(self, *args, **options):
        sent, retried, gave_up = send_pending_sms(limit=options["limit"])
        self.stdout.write(f"SMS: {sent} sent, {retried} will be retried, {gave_up} gave up.")
