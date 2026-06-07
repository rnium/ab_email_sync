from datetime import datetime
from email.utils import parsedate_to_datetime
from typing import Any

from mailsync.data_models import (
    Account,
    Category,
    CategoryGroup,
    Payee,
    Transaction,
    TransactionType,
)
from mailsync.models import BankAccount, BankMailConfig

from .actual_utils import (
    ENDPOINT_ACCOUNTS,
    ENDPOINT_CATEGORY_GROUPS,
    ENDPOINT_PAYEES,
    api_get,
    api_post,
    endpoint_import_transactions,
)

# ---------------------------------------------------------------------------
# Read services
# ---------------------------------------------------------------------------


def get_accounts() -> list[Account]:
    """Return all accounts from the Actual Budget API."""
    data = api_get(ENDPOINT_ACCOUNTS)
    return [
        Account(
            id=item["id"],
            name=item["name"],
            offbudget=item["offbudget"],
            closed=item["closed"],
            note=item.get("note"),
            balance_current=item["balance_current"],
        )
        for item in data
    ]


def get_payees() -> list[Payee]:
    """Return all payees from the Actual Budget API."""
    data = api_get(ENDPOINT_PAYEES)
    return [
        Payee(
            id=item["id"],
            name=item["name"],
            category=item.get("category"),
            transfer_acct=item.get("transfer_acct"),
        )
        for item in data
    ]


def get_category_groups(hidden: bool | None = None) -> list[CategoryGroup]:
    """Return all category groups, each containing their categories.

    Args:
        hidden: When ``True`` include hidden groups/categories.
                When ``False`` exclude them. ``None`` uses the API default.
    """
    params: dict[str, str] | None = None
    if hidden is not None:
        params = {"hidden": str(hidden).lower()}

    data = api_get(ENDPOINT_CATEGORY_GROUPS, params=params)

    groups: list[CategoryGroup] = []
    for item in data:
        categories = [
            Category(
                id=cat["id"],
                name=cat["name"],
                is_income=cat["is_income"],
                hidden=cat["hidden"],
                group_id=cat["group_id"],
                sort_order=cat.get("sort_order"),
                tombstone=cat.get("tombstone"),
            )
            for cat in item.get("categories", [])
        ]
        groups.append(
            CategoryGroup(
                id=item["id"],
                name=item["name"],
                is_income=item["is_income"],
                hidden=item["hidden"],
                categories=categories,
                sort_order=item.get("sort_order"),
                tombstone=item.get("tombstone"),
            )
        )
    return groups


def get_categories(hidden: bool | None = None) -> list[Category]:
    """Return a flat list of all categories across every group.

    Args:
        hidden: Forwarded to :func:`get_category_groups`.
    """
    groups = get_category_groups(hidden=hidden)
    return [cat for group in groups for cat in group.categories]


# ---------------------------------------------------------------------------
# Import service
# ---------------------------------------------------------------------------


def _parse_or_get_current_date(date_str: str) -> str:
    """Normalise any date string coming from an email header to YYYY-MM-DD."""
    try:
        return parsedate_to_datetime(date_str).strftime("%Y-%m-%d")
    except Exception:
        for fmt in ("%a, %d %b %Y", "%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%d-%m-%Y"):
            try:
                return datetime.strptime(date_str, fmt).strftime("%Y-%m-%d")
            except ValueError:
                continue
        return datetime.now().strftime("%Y-%m-%d")


def _get_payee_id(bank_acct: BankAccount, conf: BankMailConfig) -> str | None:
    if payee_id := bank_acct.actual_budget_payee_id:
        return payee_id
    else:
        all_payees = get_payees()
        payee_name = (
            conf.bank_account.actual_budget_payee_name
            or conf.bank_account.actual_budget_account_name
        )
        payee = list(filter(lambda p: p.name == payee_name, all_payees))
        if len(payee) > 0:
            return payee[0].id


def _build_transaction_payload(trx: Transaction) -> dict[str, Any]:
    """Convert a :class:`Transaction` domain object to the API request shape."""
    # Outgoing money is negative in Actual Budget
    signed_amount = (
        trx.amount if trx.transaction_type == TransactionType.INCOMING else -trx.amount
    )

    payload: dict[str, Any] = {
        "date": _parse_or_get_current_date(trx.date),
        "amount": signed_amount,
        "imported_id": str(hash(trx)),
        "notes": trx.ab_note or trx.subject,
    }

    if trx.ab_category:
        payload["category"] = trx.ab_category

    # For transfers, set payee id
    if trx.to_trx and trx.to_trx.mail_config and trx.to_trx.mail_config.bank_account:
        if payee_id := _get_payee_id(
            trx.to_trx.mail_config.bank_account, trx.to_trx.mail_config
        ):
            payload["payee"] = payee_id

    return payload


def import_transactions(
    account_id: str,
    transactions: list[Transaction],
    opts: dict[str, Any] | None = None,
) -> Any:
    """Import a list of transactions into the given Actual Budget account.

    Args:
        account_id: The Actual Budget account UUID to import into.
        transactions: Domain :class:`Transaction` objects to import.
        opts: Optional import options (``defaultCleared``, ``dryRun``, etc.).

    Returns:
        The API response data (added/updated/updatedPreview lists).
    """
    body: dict[str, Any] = {
        "transactions": [_build_transaction_payload(trx) for trx in transactions],
    }
    if opts:
        body["opts"] = opts

    return api_post(endpoint_import_transactions(account_id), body)
