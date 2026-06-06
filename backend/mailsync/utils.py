from typing import List

from .builder import build_transaction, consolidate_transactions
from .data_models import EmailMessage, Transaction


def get_transactions(messages: List[EmailMessage]) -> List[Transaction]:
    transactions = []
    for message in messages:
        if trx := build_transaction(message):
            transactions.append(trx)
    return consolidate_transactions(transactions)
