from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.guests.models import Guest


class Command(BaseCommand):
    help = (
        "Erase the personal details (name, national ID, phone) of guests who "
        "checked out more than --days ago, keeping their tickets and the "
        "hotel's statistics intact.\n\n"
        "NOT scheduled and NOT run by anything: retention is the hotel's "
        "decision, so this only ever runs when somebody types it. It also "
        "refuses to change anything without --confirm."
    )

    def add_arguments(self, parser):
        parser.add_argument("--days", type=int, default=365, help="Checked out at least this long ago.")
        parser.add_argument(
            "--confirm",
            action="store_true",
            help="Actually anonymise. Without it, this is a dry run that only lists.",
        )

    def handle(self, *args, **options):
        cutoff = timezone.now() - timedelta(days=options["days"])
        departed = Guest.objects.filter(checked_out_at__lt=cutoff).exclude(national_id__startswith="erased-")

        for guest in departed:
            self.stdout.write(f"  {guest.full_name} ({guest.national_id}) — left {guest.checked_out_at:%Y-%m-%d}")

        if not options["confirm"]:
            self.stdout.write(
                self.style.WARNING(
                    f"{departed.count()} guest(s) would be anonymised. "
                    "Nothing changed — add --confirm to go ahead."
                )
            )
            return

        erased = 0
        for guest in departed:
            # The rows stay (tickets point at them); only what identifies a
            # person is replaced, and the login can never match again.
            guest.full_name = "مهمان پیشین"
            guest.phone = ""
            guest.national_id = f"erased-{guest.pk}"
            guest.reservation_id = ""
            guest.save(update_fields=["full_name", "phone", "national_id", "reservation_id"])
            guest.user.username = f"erased_guest_{guest.pk}"
            guest.user.is_active = False
            guest.user.save(update_fields=["username", "is_active"])
            erased += 1

        self.stdout.write(self.style.SUCCESS(f"{erased} guest(s) anonymised."))
