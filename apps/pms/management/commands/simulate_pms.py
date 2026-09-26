import json

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from apps.pms.models import PmsEvent
from apps.pms.services import apply_event


class Command(BaseCommand):
    help = (
        "Stand in for the PMS: apply one event as if Harris had sent it. "
        "Lets the whole check-in / check-out flow be tested before the real "
        "integration exists.\n\n"
        "  python manage.py simulate_pms check_in --room 305 "
        "--national-id 0011122233 --name 'سارا احمدی' --phone 09121112233\n"
        "  python manage.py simulate_pms check_out --room 305\n"
        "  python manage.py simulate_pms room_change --room 305 --new-room 410"
    )

    def add_arguments(self, parser):
        parser.add_argument("event", choices=[choice.value for choice in PmsEvent.Type])
        parser.add_argument("--room")
        parser.add_argument("--new-room")
        parser.add_argument("--national-id")
        parser.add_argument("--name")
        parser.add_argument("--phone")
        parser.add_argument("--reservation-id")
        parser.add_argument("--until", help="Expected check-out date, YYYY-MM-DD.")

    def handle(self, *args, **options):
        payload = {
            "event": options["event"],
            "event_id": f"SIM-{timezone.now().timestamp():.0f}",
            "occurred_at": timezone.now().isoformat(),
            "room_number": options["room"],
            "new_room_number": options["new_room"],
            "reservation_id": options["reservation_id"],
            "expected_check_out": options["until"],
            "guest": {
                "full_name": options["name"],
                "national_id": options["national_id"],
                "phone": options["phone"],
            },
        }
        payload = {key: value for key, value in payload.items() if value is not None}

        event = apply_event(payload, source=PmsEvent.Source.SIMULATOR)
        self.stdout.write(json.dumps(payload, ensure_ascii=False, indent=2))
        if event.status == PmsEvent.Status.PROCESSED:
            self.stdout.write(self.style.SUCCESS(f"[{event.status}] {event.error}"))
        else:
            raise CommandError(f"[{event.status}] {event.error}")
