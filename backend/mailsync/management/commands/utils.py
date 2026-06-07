from collections import defaultdict
from typing import AnyStr, Dict, List

from mailsync.data_models import Transaction, TransactionType
from mailsync.models import BankMailConfig, SyncLog
from mailsync.services.actual import get_accounts, get_categories

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
    ab_all_accounts = get_accounts()
    ab_account_id_map = {ac.name: ac.id for ac in ab_all_accounts}

    for trx in transactions:
        config: BankMailConfig = trx.mail_config
        # Set Account Id
        if config and config.bank_account:
            if ac_id := config.bank_account.actual_budget_account_id:
                trx.ab_account_id = ac_id
            else:
                trx.ab_account_id = ab_account_id_map[
                    config.bank_account.actual_budget_account_name
                ]

        # Set tag and category, for salary deposit
        if (
            config
            and config.bank_account.is_salary_account
            and trx.transaction_type == TransactionType.INCOMING
            and trx.amount == config.bank_account.salary_amount
        ):
            trx.ab_note = config.bank_account.salary_tagname
            # set category
            categories = list(
                filter(
                    lambda cat: cat.is_income and cat.name == "Income", get_categories()
                )
            )
            if len(categories) > 0:
                trx.ab_category = categories[0].id


def group_transactions_by_account(transactions: TrxList) -> Dict[AnyStr, TrxList]:
    groups = defaultdict(list)
    for trx in transactions:
        groups[trx.ab_account_id].append(trx)

    return dict(groups)
