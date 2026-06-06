from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


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
        to_trx: "Transaction | None" = None,
        mail_config: Any = None,
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
        self.to_trx = to_trx
        self.ab_note = ""
        self.ab_category = ""
        self.mail_config = mail_config

    def __hash__(self):
        return hash(
            (self.from_name, self.subject, self.date, self.amount, hash(self.to_trx))
        )


@dataclass
class Account:
    id: str
    name: str
    offbudget: bool
    closed: bool
    note: str | None
    balance_current: float


@dataclass
class Payee:
    id: str
    name: str
    category: str | None
    transfer_acct: str | None


@dataclass
class Category:
    id: str
    name: str
    is_income: bool
    hidden: bool
    group_id: str
    sort_order: float | None = None
    tombstone: bool | None = None


@dataclass
class CategoryGroup:
    id: str
    name: str
    is_income: bool
    hidden: bool
    categories: list["Category"] = field(default_factory=list)
    sort_order: float | None = None
    tombstone: bool | None = None
