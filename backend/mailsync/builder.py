import re
from email.utils import parseaddr
from typing import List

from .data_models import EmailElement, EmailMessage, Transaction, TransactionType
from .models import BankMailConfig, SyncLog


def deduce_transaction_type(
    conf: BankMailConfig, msg: EmailMessage
) -> TransactionType | None:
    targets = []
    match conf.direction_is_in:
        case EmailElement.SUBJECT:
            targets.append(msg.subject)
        case EmailElement.BODY:
            targets.extend([msg.text, msg.snippet])
    if not targets:
        return None
    match = None
    for target in targets:
        if match := re.search(conf.direction_regex, target, flags=re.IGNORECASE):
            break

    if not match:
        return
    return TransactionType(conf.direction)


def amount_str_to_float(amount_str: str) -> float | None:
    amount_cleaned = amount_str.replace(",", "")
    try:
        amount = float(amount_cleaned)
        return amount
    except ValueError:
        return None


def deduce_amount(conf: BankMailConfig, msg: EmailMessage) -> float | None:
    targets = []
    match conf.amount_is_in:
        case EmailElement.SUBJECT:
            targets.append(msg.subject)
        case EmailElement.BODY:
            targets.extend([msg.text, msg.snippet])

    if not targets:
        return None

    match = None
    for target in targets:
        match = re.search(conf.amount_regex, target, flags=re.IGNORECASE)
        if match:
            break
    if not match:
        return None

    return amount_str_to_float(match.group(1))


def build_transaction(message: EmailMessage) -> Transaction | None:
    _, sender_addr = parseaddr(message.sender)
    sender = (sender_addr or message.sender).lower()
    mail_confs = BankMailConfig.objects.filter(from_name=sender)
    if mail_confs.count() < 1:
        return
    conf = None
    transaction_type = None
    for c in mail_confs:
        if re.search(c.subject, message.subject, flags=re.IGNORECASE):
            transaction_type = deduce_transaction_type(c, message)
            if not transaction_type:
                continue
            conf = c
            break
    if not conf:
        return None

    amount = deduce_amount(conf, message)

    if transaction_type is None or amount is None:
        return None

    return Transaction(
        from_name=message.sender,
        subject=message.subject,
        date=message.date_str,
        transaction_type=transaction_type,
        amount=amount,
        mail_config=conf,
    )


def deduplicate_transactions(transactions: List[Transaction]) -> List[Transaction]:
    """Drop duplicate notifications of the same transaction.

    A bank may send several emails for one transaction, possibly from different
    addresses (``from_name``), so duplicates are keyed on the bank account,
    direction, time and amount rather than the sender. Only the first of each
    such group is kept.
    """
    seen = set()
    deduped: List[Transaction] = []
    for trx in transactions:
        if trx.mail_config is not None:
            key = (
                trx.mail_config.bank_account_id,
                trx.transaction_type,
                trx.date,
                trx.amount,
            )
        else:
            key = (
                trx.from_name,
                trx.subject,
                trx.transaction_type,
                trx.date,
                trx.amount,
            )
        if key in seen:
            continue
        seen.add(key)
        deduped.append(trx)
    return deduped


def consolidate_transactions(transactions: List[Transaction]) -> List[Transaction]:
    if len(transactions) < 2:
        return transactions
    types = set([tr.transaction_type for tr in transactions])
    if len(types) < 2:
        return transactions
    out_transactions = filter(
        lambda tr: tr.transaction_type == TransactionType.OUTGOING, transactions
    )
    removables: List[Transaction] = []

    for o_trx in out_transactions:
        in_transactions = list(
            filter(
                lambda tr: (
                    tr.transaction_type == TransactionType.INCOMING
                    and tr.amount == o_trx.amount
                    and (
                        tr.mail_config is None
                        or o_trx.mail_config is None
                        or tr.mail_config.bank_account != o_trx.mail_config.bank_account
                    )
                ),
                transactions,
            )
        )
        if len(in_transactions) == 0:
            continue

        o_trx.to_trx = in_transactions[0]
        removables.append(in_transactions[0])

    consolidated = list(filter(lambda tr: tr not in removables, transactions))
    return consolidated


def filter_synced(transactions: List[Transaction]) -> List[Transaction]:
    synced = set(
        SyncLog.objects.filter(
            transaction_hash__in=[str(hash(trx)) for trx in transactions]
        ).values_list("transaction_hash", flat=True)
    )
    return [trx for trx in transactions if str(hash(trx)) not in synced]


def get_transactions(messages: List[EmailMessage]) -> List[Transaction]:
    transactions = []
    for message in messages:
        if trx := build_transaction(message):
            transactions.append(trx)
    transactions = deduplicate_transactions(transactions)
    transactions = filter_synced(transactions)
    return consolidate_transactions(transactions)
