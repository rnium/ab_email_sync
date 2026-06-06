from typing import List

from django.conf import settings
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow, json
from googleapiclient.discovery import build
from mailsync.data_models import EmailMessage
from mailsync.models import Configuration as Config
from .gmail_utils import get_message_body

SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]


def get_gmail_service():
    creds = None
    if tok_config := Config.objects.filter(key=settings.GMAIL_TOKEN_KEY).first():
        token_data = json.loads(tok_config.value)
        creds = Credentials.from_authorized_user_info(token_data, SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            creds_config = Config.objects.filter(key=settings.GMAIL_CONFIG_KEY).first()
            if not creds_config:
                raise AttributeError("Credentials json not set")
            creds_data = json.loads(creds_config.value)
            flow = InstalledAppFlow.from_client_config(creds_data, SCOPES)
            creds = flow.run_local_server(port=0)
        tok_config, _created = Config.objects.get_or_create(
            key=settings.GMAIL_TOKEN_KEY
        )
        tok_config.value = creds.to_json()
        tok_config.save()
    return build("gmail", "v1", credentials=creds)


def get_primary_unread_messages(
    max_results=settings.EMAIL_MAX_RESULTS, days=settings.EMAIL_MAX_AGE
) -> List[EmailMessage]:
    service = get_gmail_service()
    results = (
        service.users()
        .threads()
        .list(
            userId="me",
            q=f"is:unread is:inbox category:primary newer_than:{days}d",
            maxResults=max_results,
        )
        .execute()
    )

    threads = results.get("threads", [])

    if not threads:
        return []

    all_messages = []

    for thread in threads:
        thread_data = (
            service.users()
            .threads()
            .get(
                userId="me",
                id=thread["id"],
                format="metadata",
                metadataHeaders=["Subject", "From", "Date"],
            )
            .execute()
        )

        messages = thread_data.get("messages", [])
        email_messages = []
        for message in messages:
            headers = message["payload"]["headers"]
            subject = next(
                (h["value"] for h in headers if h["name"] == "Subject"), "No Subject"
            )
            sender = next(
                (h["value"] for h in headers if h["name"] == "From"), "Unknown"
            )
            date = next((h["value"] for h in headers if h["name"] == "Date"), "Unknown")
            email_messages.append(
                EmailMessage(
                    subject=subject,
                    sender=sender,
                    date_str=date,
                    text=get_message_body(message["payload"]),
                    snippet=message.get("snippet", ""),
                )
            )

        all_messages.extend(email_messages)

    return all_messages
