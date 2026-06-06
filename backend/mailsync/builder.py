import re
from typing import List

from .data_models import EmailElement, EmailMessage, Transaction, TransactionType
from .models import BankMailConfig


def deduce_transaction_type(
    conf: BankMailConfig, msg: EmailMessage
) -> TransactionType | None:
    target_str = ""
    match conf.direction_is_in:
        case EmailElement.SUBJECT:
            target_str = msg.subject
        case EmailElement.BODY:
            target_str = msg.text
    if not target_str:
        return None
    if re.search(conf.direction_regex, target_str, flags=re.IGNORECASE) is None:
        return None

    return TransactionType(conf.direction)


def amount_str_to_float(amount_str: str) -> float | None:
    amount_cleaned = amount_str.replace(",", "")
    try:
        amount = float(amount_cleaned)
        return amount
    except ValueError:
        return None


def deduce_amount(conf: BankMailConfig, msg: EmailMessage) -> float | None:
    target_str = ""
    match conf.amount_is_in:
        case EmailElement.SUBJECT:
            target_str = msg.subject
        case EmailElement.BODY:
            target_str = msg.text
    if not target_str:
        return None

    match = re.search(conf.amount_regex, target_str, flags=re.IGNORECASE)
    if not match:
        return None

    return amount_str_to_float(match.group(1))


def build_transaction(message: EmailMessage) -> Transaction | None:
    mail_confs = BankMailConfig.objects.filter(from_name=message.sender)
    if mail_confs.count() < 1:
        return
    conf = None
    for c in mail_confs:
        if re.search(c.subject, message.subject, flags=re.IGNORECASE):
            conf = c
            break
    if not conf:
        return None

    transaction_type = deduce_transaction_type(conf, message)
    amount = deduce_amount(conf, message)

    if transaction_type is None or amount is None:
        return None

    return Transaction(
        from_name=message.sender,
        subject=message.subject,
        date=message.date_str,
        transaction_type=transaction_type,
        amount=amount,
    )

def consolidate_transactions(transactions: List[Transaction]) -> List[Transaction]:
    return transactions
