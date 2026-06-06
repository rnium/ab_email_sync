from dataclasses import dataclass
from enum import StrEnum


class TransactionType(StrEnum):
    INCOMING = "incoming"
    OUTGOING = "outgoing"


class EmailElement(StrEnum):
    SUBJECT = "subject"
    BODY = "body"


@dataclass
class EmailMessage:
    subject: str
    sender: str
    date_str: str
    text: str
    snippet: str


class Transaction:
    def __init__(
        self,
        from_name: str,
        subject: str,
        date: str,
        amount: float,
        transaction_type: TransactionType,
        to_name=None,
    ):
        if not isinstance(amount, float):
            raise ValueError("amount must be a float")
        if amount < 0:
            raise ValueError("amount must be non-negative")
        self.from_name = from_name
        self.subject = subject
        self.date = date
        self.amount = amount
        self.transaction_type = transaction_type
        self.to_name = to_name

    def __hash__(self):
        return hash(
            (self.from_name, self.subject, self.date, self.amount, self.to_name)
        )
