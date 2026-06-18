from typing import List

from mailsync.data_models import Transaction, TransactionType
from mailsync.models import BankMailConfig, SyncLog
from mailsync.services.actual import get_accounts, get_categories

type TrxList = List[Transaction]


def _make_sync_log(trx: Transaction, success: bool, error_message: str | None = None) -> SyncLog:
    if trx.to_trx:
        txtype = "transfer"
    elif trx.transaction_type == TransactionType.INCOMING:
        txtype = "deposit"
    else:
        txtype = "withdrawal"
    return SyncLog(
        transaction_type=txtype,
        transaction_amount=trx.amount,
        bank_mail=trx.mail_config,
        success=success,
        error_message=error_message,
        transaction_hash=str(hash(trx)),
    )


def log_sync_result(trx: Transaction, res: dict):
    errors = res.get("errors") or []
    updated = res.get("updated") or []

    if errors:
        err = errors[0]
        err_msg = err.get("message", str(err)) if isinstance(err, dict) else str(err)
        log = _make_sync_log(trx, success=False, error_message=err_msg)
    elif updated:
        msg = (
            f"Updated | from: {trx.from_name} | subject: {trx.subject}"
            f" | date: {trx.date} | amount: {trx.amount}"
        )
        log = _make_sync_log(trx, success=True, error_message=msg)
    else:
        log = _make_sync_log(trx, success=True)

    log.save()
    _log_consumed_leg(trx, log)


def _log_consumed_leg(trx: Transaction, transfer_log: SyncLog):
    """Record the incoming leg consumed into a transfer.

    A transfer is synced as the single outgoing transaction; its incoming
    counterpart (``trx.to_trx``) is dropped during consolidation and would
    otherwise never reach SyncLog, letting it re-sync as a standalone deposit
    if it later reappears without its outgoing leg. Mirror the transfer's
    outcome so the incoming email can't be processed again.
    """
    if trx.to_trx is None:
        return
    _make_sync_log(
        trx.to_trx,
        success=transfer_log.success,
        error_message=transfer_log.error_message,
    ).save()


def log_sync_error(trx: Transaction, error_message: str):
    log = _make_sync_log(trx, success=False, error_message=error_message)
    log.save()
    _log_consumed_leg(trx, log)


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
