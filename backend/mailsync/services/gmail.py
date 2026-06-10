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
        try:
            token_data = json.loads(tok_config.value)
            creds = Credentials.from_authorized_user_info(token_data, SCOPES)
        except Exception:
            pass

    if not creds or not creds.valid:
        creds_config = None
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            creds_config = Config.objects.filter(key=settings.GMAIL_CONFIG_KEY).first()
            if not (creds_config and creds_config.value):
                raise AttributeError("Credentials json not set")
            creds_data = json.loads(creds_config.value)
            flow = InstalledAppFlow.from_client_config(creds_data, SCOPES)
            creds = flow.run_local_server(port=0)
        tok_config, created = Config.objects.get_or_create(
            key=settings.GMAIL_TOKEN_KEY,
            defaults={
                "parent": creds_config,
                "label": "Gmail Token JSON",
            },
        )
        tok_config.value = creds.to_json()
        tok_config.save()
    return build("gmail", "v1", credentials=creds)


def get_primary_unread_messages(
    max_results=settings.EMAIL_MAX_RESULTS, days=settings.EMAIL_MAX_AGE
) -> List[EmailMessage]:
    service = get_gmail_service()

    # Step 1: list thread IDs matching the query (cheap call)
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

    # Step 2: batch-fetch every thread with full format in one HTTP round-trip
    fetched: dict[str, dict] = {}

    def _store(request_id, response, exception):
        if exception is None and response:
            fetched[request_id] = response

    batch = service.new_batch_http_request(callback=_store)
    for thread in threads:
        batch.add(
            service.users()
            .threads()
            .get(
                userId="me",
                id=thread["id"],
                format="full",
            ),
            request_id=thread["id"],
        )
    batch.execute()

    # Step 3: flatten all messages from every thread into a single list
    all_messages: List[EmailMessage] = []
    for thread_id, thread_data in fetched.items():
        for message in thread_data.get("messages", []):
            headers = message.get("payload", {}).get("headers", [])
            subject = next(
                (h["value"] for h in headers if h["name"].lower() == "subject"),
                "No Subject",
            )
            sender = next(
                (h["value"] for h in headers if h["name"].lower() == "from"),
                "Unknown",
            )
            date = next(
                (h["value"] for h in headers if h["name"].lower() == "date"),
                "Unknown",
            )
            all_messages.append(
                EmailMessage(
                    subject=subject,
                    sender=sender,
                    date_str=date,
                    text=get_message_body(message.get("payload", {})),
                    snippet=message.get("snippet", ""),
                )
            )

    return all_messages
