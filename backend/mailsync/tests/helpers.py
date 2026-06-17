import base64

from ..data_models import EmailMessage, Transaction, TransactionType


def make_message(
    *,
    subject="Card credited abc",
    sender="alerts@example.com",
    date_str="2026-06-06",
    text="Amount: BDT 1,234.50",
):
    return EmailMessage(
        subject=subject,
        sender=sender,
        date_str=date_str,
        text=text,
        snippet="",
    )


def make_transaction(
    subject,
    *,
    amount=1.0,
    transaction_type=TransactionType.INCOMING,
):
    return Transaction(
        from_name="alerts@example.com",
        subject=subject,
        date="2026-06-06",
        amount=amount,
        transaction_type=transaction_type,
    )


def encoded_body(text):
    data = base64.urlsafe_b64encode(text.encode()).decode().rstrip("=")
    return {"data": data}
