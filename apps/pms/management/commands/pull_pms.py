from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.pms.client import PmsUnavailable, get_client
from apps.pms.models import PmsEvent, PmsSyncState
from apps.pms.services import apply_event


class Command(BaseCommand):
    help = (
        "Ask the PMS what changed since the last run and apply it "
        "(check-ins, check-outs, room changes). Meant to run every few "
        "minutes from Windows Task Scheduler: python manage.py pull_pms. "
        "Safe to run often — an event already applied is skipped."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--since",
            type=timezone.datetime.fromisoformat,
            help="Ignore the stored cursor and ask from this moment (ISO 8601).",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Fetch and show what would be applied, without changing anything.",
        )

    def handle(self, *args, **options):
        state = PmsSyncState.load()
        since = options["since"] or state.last_synced_at
        started = timezone.now()

        try:
            events = get_client().fetch_events(since=since)
        except PmsUnavailable as exc:
            # Not a crash: the PMS being down is an expected condition, and
            # the next run picks up from the same cursor.
            state.last_run_at = started
            state.last_error = str(exc)
            state.save()
            self.stdout.write(self.style.WARNING(f"PMS unavailable: {exc}"))
            return

        if options["dry_run"]:
            for event in events:
                self.stdout.write(f"  would apply: {event}")
            self.stdout.write(self.style.SUCCESS(f"{len(events)} event(s) waiting (dry run)."))
            return

        counts = {}
        for payload in events:
            applied = apply_event(payload, source=PmsEvent.Source.PULL)
            counts[applied.status] = counts.get(applied.status, 0) + 1
            self.stdout.write(f"  [{applied.status}] {applied.event_type or '?'}: {applied.error}")

        state.last_synced_at = started
        state.last_run_at = started
        state.last_error = ""
        state.save()

        summary = ", ".join(f"{count} {status.lower()}" for status, count in sorted(counts.items())) or "nothing new"
        self.stdout.write(self.style.SUCCESS(f"PMS pull done: {summary}."))
