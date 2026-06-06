from typing import List

from mailsync.data_models import Transaction, TransactionType
from mailsync.models import BankMailConfig, SyncLog

type TrxList = List[Transaction]


def filter_transactions(transactions: TrxList) -> TrxList:
    synced_hashes = [
        log.transaction_hash
        for log in SyncLog.objects.filter(
            transaction_hash__in=[hash(trx) for trx in transactions]
        )
    ]

    return list(filter(lambda trx: hash(trx) not in synced_hashes, transactions))

def set_ab_properties(transactions: TrxList):
    for trx in transactions:
        config: BankMailConfig = trx.mail_config
    
        # for salary deposit
        if config and config.bank_account.is_salary_account and trx.transaction_type == TransactionType.INCOMING and trx.amount == config.bank_account.salary_amount:
            trx.ab_note = config.bank_account.salary_tagname
            #TODO: fetch income category from api and set in trx