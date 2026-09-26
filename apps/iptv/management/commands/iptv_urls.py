from django.conf import settings
from django.core.management.base import BaseCommand

from apps.iptv.auth import signature_for
from apps.rooms.models import Room


class Command(BaseCommand):
    """
    The list the IPTV company asks for: one URL per room, to be set as
    that room's page on its set-top box. When IPTV_PAGE_SECRET is set,
    each URL carries its own signature, so changing the room number in
    a URL doesn't show somebody else's requests.
    """

    help = (
        "Print the in-room television URL for every room, ready to hand "
        "to the IPTV company.\n\n"
        "  python manage.py iptv_urls --base-url https://hotel.example.com\n"
        "  python manage.py iptv_urls --base-url https://hotel.example.com --csv > tv-urls.csv"
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--base-url",
            default=getattr(settings, "IPTV_BASE_URL", "") or "http://localhost:8000",
            help="How the televisions reach this server (scheme and host).",
        )
        parser.add_argument("--csv", action="store_true", help="room_number,url per line.")

    def handle(self, *args, **options):
        base = options["base_url"].rstrip("/")
        rooms = Room.objects.order_by("number")
        if not rooms:
            self.stdout.write(self.style.WARNING("No rooms are defined yet."))
            return

        if options["csv"]:
            self.stdout.write("room_number,url")
        for room in rooms:
            signature = signature_for(room.number)
            url = f"{base}/tv/{room.number}/"
            if signature:
                url = f"{url}?t={signature}"
            self.stdout.write(f"{room.number},{url}" if options["csv"] else f"  {room.number}: {url}")

        if not signature_for(rooms[0].number):
            self.stdout.write(
                self.style.WARNING(
                    "\nIPTV_PAGE_SECRET is not set, so these URLs carry no signature: "
                    "the page then relies on IPTV_ALLOWED_NETWORKS alone, and is "
                    "refused entirely if that is unset too."
                )
            )
