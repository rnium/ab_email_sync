from django.conf import settings
from django.core.management.base import BaseCommand

from mailsync.models import Configuration

CONFIGURATIONS = [
    {
        "key": settings.ACTUAL_BUDGET_PASSWORD_KEY,
        "label": "Actual Budget Password",
        "value": "",
    },
    {
        "key": settings.ACTUAL_BUDGET_SYNC_ID_KEY,
        "label": "Actual Budget Sync ID",
        "value": "",
    },
    {"key": settings.GMAIL_CONFIG_KEY, "label": "Gmail Credential JSON", "value": ""},
    {
        "key": settings.SCHEDULER_DAYTIME_START_KEY,
        "label": "Scheduler – Daytime Start (hour, 0–23)",
        "value": "8",
    },
    {
        "key": settings.SCHEDULER_DAYTIME_END_KEY,
        "label": "Scheduler – Daytime End (hour, 0–23)",
        "value": "23",
    },
    {
        "key": settings.SCHEDULER_DAYTIME_INTERVAL_KEY,
        "label": "Scheduler – Daytime Interval (minutes)",
        "value": "5",
    },
    {
        "key": settings.SCHEDULER_NIGHTTIME_INTERVAL_KEY,
        "label": "Scheduler – Nighttime Interval (minutes)",
        "value": "15",
    },
]


class Command(BaseCommand):
    help = "Seed the database with the required system configuration keys and their default values."

    def handle(self, *args, **options):
        created_count = 0
        skipped_count = 0

        for config in CONFIGURATIONS:
            _, created = Configuration.objects.get_or_create(
                key=config["key"],
                defaults={
                    "label": config["label"],
                    "value": config["value"],
                },
            )
            if created:
                created_count += 1
                self.stdout.write(self.style.SUCCESS(f"  Created: {config['key']}"))
            else:
                skipped_count += 1
                self.stdout.write(
                    self.style.WARNING(f"  Skipped: {config['key']} (already exists)")
                )

        self.stdout.write(
            self.style.SUCCESS(
                f"\nDone. {created_count} created, {skipped_count} already present."
            )
        )
