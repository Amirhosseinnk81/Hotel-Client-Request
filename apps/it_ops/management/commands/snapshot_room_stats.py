from datetime import date, timedelta

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from apps.it_ops.services import snapshot_room_stats


class Command(BaseCommand):
    help = (
        "Store the RoomDailyStat row for a day, computed from the real Room "
        "data (today: live room status; a past day: rebuilt from "
        "RoomStatusLog). Safe to re-run — the day's row is updated, not "
        "duplicated. Meant to run nightly from Windows Task Scheduler, e.g. "
        "at 23:55: python manage.py snapshot_room_stats"
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--date",
            type=date.fromisoformat,
            help="Day to snapshot, YYYY-MM-DD (default: today).",
        )
        parser.add_argument(
            "--days",
            type=int,
            default=1,
            help="Also backfill this many days ending at --date (default 1 = just that day).",
        )

    def handle(self, *args, **options):
        today = timezone.localdate()
        last_day = options["date"] or today
        if last_day > today:
            raise CommandError("Cannot snapshot a day that has not happened yet.")
        if options["days"] < 1:
            raise CommandError("--days must be at least 1.")

        for offset in range(options["days"] - 1, -1, -1):
            stat = snapshot_room_stats(last_day - timedelta(days=offset))
            self.stdout.write(
                f"  {stat.date}: {stat.occupied_rooms}/{stat.total_rooms} occupied, "
                f"{stat.vacant_rooms} vacant, {stat.out_of_order_rooms} out of order "
                f"({stat.occupancy_rate}%)"
            )
        self.stdout.write(self.style.SUCCESS("Room stats snapshot done."))
