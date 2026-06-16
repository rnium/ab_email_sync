from django.conf import settings
from django.core.management.base import BaseCommand
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow, json

from mailsync.models import Configuration as Config

SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]


class Command(BaseCommand):
    help = "Run the Gmail OAuth flow and store the resulting token in the database."

    def handle(self, *args, **options):
        creds_config = Config.objects.filter(key=settings.GMAIL_CONFIG_KEY).first()
        if not (creds_config and creds_config.value):
            self.stderr.write(
                self.style.ERROR("Gmail credentials JSON not set in Configuration.")
            )
            return

        creds_data = json.loads(creds_config.value)
        flow = InstalledAppFlow.from_client_config(creds_data, SCOPES)
        creds: Credentials = flow.run_local_server(port=0)

        tok_config, _ = Config.objects.get_or_create(
            key=settings.GMAIL_TOKEN_KEY,
            defaults={
                "parent": creds_config,
                "label": "Gmail Token JSON",
            },
        )
        tok_config.value = creds.to_json()
        tok_config.save()
        self.stdout.write(self.style.SUCCESS("Gmail token saved successfully."))
