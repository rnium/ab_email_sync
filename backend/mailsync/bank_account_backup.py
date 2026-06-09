import json
from decimal import Decimal
from typing import Any

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from .models import BankAccount, BankMailConfig

BACKUP_FORMAT = "mailsync.bank-accounts"
BACKUP_VERSION = 1
MAX_BACKUP_SIZE = 2 * 1024 * 1024

ACCOUNT_FIELDS = (
    "bank_name",
    "account_number",
    "actual_budget_account_name",
    "actual_budget_account_id",
    "actual_budget_payee_name",
    "actual_budget_payee_id",
    "is_salary_account",
    "salary_amount",
    "salary_tagname",
)
RULE_FIELDS = (
    "direction",
    "from_name",
    "subject",
    "direction_is_in",
    "direction_regex",
    "amount_is_in",
    "amount_regex",
)
RULE_IDENTITY_FIELDS = ("direction", "from_name", "subject")
REQUIRED_STRING_ACCOUNT_FIELDS = (
    "bank_name",
    "account_number",
    "actual_budget_account_name",
)
NULLABLE_STRING_ACCOUNT_FIELDS = (
    "actual_budget_account_id",
    "actual_budget_payee_name",
    "actual_budget_payee_id",
    "salary_tagname",
)


def export_bank_accounts() -> dict[str, Any]:
    accounts = BankAccount.objects.prefetch_related("bankmailconfig_set").all()
    return {
        "format": BACKUP_FORMAT,
        "version": BACKUP_VERSION,
        "exported_at": timezone.now().isoformat(),
        "accounts": [
            {
                **{
                    field: _serialize_value(getattr(account, field))
                    for field in ACCOUNT_FIELDS
                },
                "email_parsing_rules": [
                    {field: getattr(rule, field) for field in RULE_FIELDS}
                    for rule in account.bankmailconfig_set.all()
                ],
            }
            for account in accounts
        ],
    }


def encode_backup(payload: dict[str, Any]) -> bytes:
    return json.dumps(payload, indent=2, ensure_ascii=False).encode("utf-8")


def decode_backup(uploaded_file) -> dict[str, Any]:
    if uploaded_file.size > MAX_BACKUP_SIZE:
        raise ValidationError("Backup file must be 2 MB or smaller.")

    try:
        payload = json.loads(uploaded_file.read().decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValidationError("The uploaded file is not valid UTF-8 JSON.") from error

    _validate_structure(payload)
    return payload


@transaction.atomic
def restore_bank_accounts(payload: dict[str, Any]) -> dict[str, int]:
    _validate_structure(payload)
    counts = {
        "accounts_created": 0,
        "accounts_updated": 0,
        "rules_created": 0,
        "rules_updated": 0,
        "rules_deleted": 0,
    }

    for account_data in payload["accounts"]:
        rules_data = account_data["email_parsing_rules"]
        account_values = {
            field: _deserialize_account_value(field, account_data[field])
            for field in ACCOUNT_FIELDS
        }
        matches = BankAccount.objects.filter(
            bank_name=account_values["bank_name"],
            account_number=account_values["account_number"],
        )
        if matches.count() > 1:
            raise ValidationError(
                "Cannot restore account "
                f"{account_values['bank_name']} - {account_values['account_number']}: "
                "multiple existing accounts have the same bank name and account number."
            )

        account = matches.first()
        if account is None:
            account = BankAccount(**account_values)
            counts["accounts_created"] += 1
        else:
            for field, value in account_values.items():
                setattr(account, field, value)
            counts["accounts_updated"] += 1

        account.full_clean()
        account.save()
        _restore_rules(account, rules_data, counts)

    return counts


def _restore_rules(
    account: BankAccount,
    rules_data: list[dict[str, Any]],
    counts: dict[str, int],
) -> None:
    existing_rules = list(account.bankmailconfig_set.all())
    unused_rules = {rule.pk: rule for rule in existing_rules}

    for rule_data in rules_data:
        identity = tuple(rule_data[field] for field in RULE_IDENTITY_FIELDS)
        rule = next(
            (
                candidate
                for candidate in unused_rules.values()
                if tuple(getattr(candidate, field) for field in RULE_IDENTITY_FIELDS)
                == identity
            ),
            None,
        )

        if rule is None:
            rule = BankMailConfig(bank_account=account)
            counts["rules_created"] += 1
        else:
            unused_rules.pop(rule.pk)
            counts["rules_updated"] += 1

        for field in RULE_FIELDS:
            setattr(rule, field, rule_data[field])
        rule.full_clean()
        rule.save()

    stale_rule_ids = list(unused_rules)
    if stale_rule_ids:
        counts["rules_deleted"] += len(stale_rule_ids)
        BankMailConfig.objects.filter(pk__in=stale_rule_ids).delete()


def _validate_structure(payload: Any) -> None:
    if not isinstance(payload, dict):
        raise ValidationError("Backup root must be a JSON object.")
    if payload.get("format") != BACKUP_FORMAT:
        raise ValidationError("This is not a bank account backup file.")
    if payload.get("version") != BACKUP_VERSION:
        raise ValidationError(
            f"Unsupported backup version. Expected version {BACKUP_VERSION}."
        )

    accounts = payload.get("accounts")
    if not isinstance(accounts, list):
        raise ValidationError("Backup accounts must be a JSON array.")

    seen_accounts = set()
    required_account_fields = set(ACCOUNT_FIELDS) | {"email_parsing_rules"}
    for index, account in enumerate(accounts, start=1):
        if not isinstance(account, dict):
            raise ValidationError(f"Account {index} must be a JSON object.")
        missing = required_account_fields - account.keys()
        if missing:
            raise ValidationError(
                f"Account {index} is missing field(s): {', '.join(sorted(missing))}."
            )

        if any(
            not isinstance(account[field], str)
            for field in REQUIRED_STRING_ACCOUNT_FIELDS
        ):
            raise ValidationError(
                f"Account {index} required text fields must be strings."
            )
        if any(
            account[field] is not None and not isinstance(account[field], str)
            for field in NULLABLE_STRING_ACCOUNT_FIELDS
        ):
            raise ValidationError(
                f"Account {index} optional text fields must be strings or null."
            )
        if not isinstance(account["is_salary_account"], bool):
            raise ValidationError(
                f"Account {index} is_salary_account must be true or false."
            )
        salary_amount = account["salary_amount"]
        if salary_amount is not None and (
            isinstance(salary_amount, bool)
            or not isinstance(salary_amount, (str, int, float))
        ):
            raise ValidationError(
                f"Account {index} salary_amount must be a number, string, or null."
            )

        identity = (account["bank_name"], account["account_number"])
        if identity in seen_accounts:
            raise ValidationError(
                f"Backup contains duplicate account: {identity[0]} - {identity[1]}."
            )
        seen_accounts.add(identity)

        rules = account["email_parsing_rules"]
        if not isinstance(rules, list):
            raise ValidationError(
                f"Account {index} email_parsing_rules must be a JSON array."
            )
        for rule_index, rule in enumerate(rules, start=1):
            if not isinstance(rule, dict):
                raise ValidationError(
                    f"Account {index}, rule {rule_index} must be a JSON object."
                )
            missing_rule_fields = set(RULE_FIELDS) - rule.keys()
            if missing_rule_fields:
                raise ValidationError(
                    f"Account {index}, rule {rule_index} is missing field(s): "
                    f"{', '.join(sorted(missing_rule_fields))}."
                )
            if any(not isinstance(rule[field], str) for field in RULE_FIELDS):
                raise ValidationError(
                    f"Account {index}, rule {rule_index} fields must be strings."
                )


def _serialize_value(value: Any) -> Any:
    if isinstance(value, Decimal):
        return str(value)
    return value


def _deserialize_account_value(field: str, value: Any) -> Any:
    if field == "salary_amount" and value not in (None, ""):
        try:
            return Decimal(str(value))
        except Exception as error:
            raise ValidationError("salary_amount must be a valid decimal value.") from error
    return value
