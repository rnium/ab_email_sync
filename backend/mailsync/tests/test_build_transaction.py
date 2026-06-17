from django.test import TestCase

from ..builder import build_transaction
from ..data_models import EmailElement, TransactionType
from ..models import BankAccount, BankMailConfig
from .helpers import make_message


class BuildTransactionTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.account = BankAccount.objects.create(
            bank_name="Example Bank",
            account_number="1234",
            actual_budget_account_name="Checking",
        )

    def create_config(self, **overrides):
        values = {
            "bank_account": self.account,
            "from_name": "alerts@example.com",
            "subject": r"card credited",
            "direction": TransactionType.INCOMING,
            "direction_is_in": EmailElement.SUBJECT,
            "direction_regex": r"credited",
            "amount_is_in": EmailElement.BODY,
            "amount_regex": r"BDT\s*([\d,]+\.\d{2})",
        }
        values.update(overrides)
        return BankMailConfig.objects.create(**values)

    def test_build_transaction_selects_matching_config_and_maps_message_fields(self):
        self.create_config(subject=r"unrelated subject")
        self.create_config(
            subject=r"CARD CREDITED",
            direction=TransactionType.OUTGOING,
            direction_regex=r"CREDITED",
        )
        message = make_message()

        transaction = build_transaction(message)

        self.assertIsNotNone(transaction)
        self.assertEqual(transaction.from_name, message.sender)
        self.assertEqual(transaction.subject, message.subject)
        self.assertEqual(transaction.date, message.date_str)
        self.assertEqual(transaction.transaction_type, TransactionType.OUTGOING)
        self.assertEqual(transaction.amount, 1234.5)

    def test_build_transaction_returns_none_when_no_config_applies(self):
        self.assertIsNone(build_transaction(make_message()))

        self.create_config(from_name="other@example.com")
        self.create_config(subject=r"debit notification")

        self.assertIsNone(build_transaction(make_message()))

    def test_build_transaction_returns_none_when_required_data_is_not_extracted(self):
        self.create_config(amount_regex=r"USD\s*([\d.]+)")

        self.assertIsNone(build_transaction(make_message()))
