import time
from datetime import datetime
from pathlib import Path

from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.db import connection
from django.db.utils import OperationalError

HEARTBEAT_FILE = Path("/tmp/scheduler_heartbeat")


class Command(BaseCommand):
    help = "Run fetch-sync on a schedule configurable from the database."

    def _wait_for_db(self) -> None:
        """Block until the database is accepting connections."""
        while True:
            try:
                connection.ensure_connection()
                return
            except OperationalError:
                self.stdout.write("Database unavailable – retrying in 2 s…")
                time.sleep(2)

    def _int_from_config(self, key: str, fallback: int) -> int:
        from mailsync.models import Configuration

        try:
            obj = Configuration.objects.filter(key=key).first()
            if obj and obj.value:
                return int(obj.value)
        except Exception:
            pass
        return fallback

    def handle(self, *args, **options) -> None:
        self._wait_for_db()
        self.stdout.write(self.style.SUCCESS("Scheduler started."))

        while True:
            now = datetime.now()

            day_start = self._int_from_config(settings.SCHEDULER_DAYTIME_START_KEY, 8)
            day_end = self._int_from_config(settings.SCHEDULER_DAYTIME_END_KEY, 23)
            day_ivl = self._int_from_config(settings.SCHEDULER_DAYTIME_INTERVAL_KEY, 5)
            night_ivl = self._int_from_config(
                settings.SCHEDULER_NIGHTTIME_INTERVAL_KEY, 15
            )

            is_day = day_start <= now.hour < day_end
            interval = day_ivl if is_day else night_ivl
            period = "daytime" if is_day else "nighttime"

            self.stdout.write(
                f"[{now.strftime('%H:%M')}] Running fetch-sync "
                f"({period}, next in {interval} min)"
            )

            try:
                call_command("fetch-sync")
                self.stdout.write(self.style.SUCCESS("fetch-sync completed."))
            except Exception as exc:
                self.stderr.write(self.style.ERROR(f"fetch-sync failed: {exc}"))

            HEARTBEAT_FILE.touch()
            time.sleep(interval * 60)
