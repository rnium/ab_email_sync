import json

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse

from ..bank_account_backup import BACKUP_FORMAT, BACKUP_VERSION
from ..data_models import EmailElement, TransactionType
from ..models import BankAccount, BankMailConfig


class BankAccountBackupAdminTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin_user = get_user_model().objects.create_superuser(
            username="admin",
            email="admin@example.com",
            password="password",
        )

    def setUp(self):
        self.client.force_login(self.admin_user)

    def create_account(self, **overrides):
        values = {
            "bank_name": "Example Bank",
            "account_number": "1234",
            "actual_budget_account_name": "Checking",
            "actual_budget_account_id": "actual-account-id",
            "actual_budget_payee_name": "Transfer Payee",
            "actual_budget_payee_id": "actual-payee-id",
            "is_salary_account": True,
            "salary_amount": "5000.50",
            "salary_tagname": "Salary",
        }
        values.update(overrides)
        return BankAccount.objects.create(**values)

    def create_rule(self, account, **overrides):
        values = {
            "bank_account": account,
            "direction": TransactionType.INCOMING,
            "from_name": "alerts@example.com",
            "subject": r"credited",
            "direction_is_in": EmailElement.SUBJECT,
            "direction_regex": r"\bcredited\b",
            "amount_is_in": EmailElement.BODY,
            "amount_regex": r"BDT\s*([\d,]+\.\d{2})",
        }
        values.update(overrides)
        return BankMailConfig.objects.create(**values)

    def backup_upload(self, payload):
        return SimpleUploadedFile(
            "bank-accounts.json",
            json.dumps(payload).encode(),
            content_type="application/json",
        )

    def test_export_download_contains_accounts_and_email_parsing_rules(self):
        account = self.create_account()
        self.create_rule(account)

        response = self.client.get(
            reverse("admin:mailsync_bankaccount_backup_export")
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/json")
        self.assertIn("attachment;", response["Content-Disposition"])
        payload = json.loads(response.content)
        self.assertEqual(payload["format"], BACKUP_FORMAT)
        self.assertEqual(payload["version"], BACKUP_VERSION)
        self.assertEqual(len(payload["accounts"]), 1)
        self.assertEqual(payload["accounts"][0]["salary_amount"], "5000.50")
        self.assertEqual(
            payload["accounts"][0]["email_parsing_rules"][0]["amount_regex"],
            r"BDT\s*([\d,]+\.\d{2})",
        )

    def test_exported_backup_can_recreate_deleted_account_and_rules(self):
        account = self.create_account()
        self.create_rule(account)
        export_response = self.client.get(
            reverse("admin:mailsync_bankaccount_backup_export")
        )
        account.delete()

        restore_response = self.client.post(
            reverse("admin:mailsync_bankaccount_backup_restore"),
            {
                "backup_file": SimpleUploadedFile(
                    "bank-accounts.json",
                    export_response.content,
                    content_type="application/json",
                )
            },
        )

        self.assertRedirects(
            restore_response,
            reverse("admin:mailsync_bankaccount_changelist"),
        )
        restored = BankAccount.objects.get(
            bank_name="Example Bank",
            account_number="1234",
        )
        self.assertEqual(restored.actual_budget_account_name, "Checking")
        self.assertEqual(restored.salary_amount, 5000.50)
        self.assertEqual(restored.bankmailconfig_set.count(), 1)
        self.assertEqual(
            restored.bankmailconfig_set.get().direction_regex,
            r"\bcredited\b",
        )

    def test_restore_updates_accounts_and_synchronizes_rules(self):
        account = self.create_account(actual_budget_account_name="Old Checking")
        matching_rule = self.create_rule(account, amount_regex=r"old amount")
        stale_rule = self.create_rule(
            account,
            direction=TransactionType.OUTGOING,
            subject=r"debited",
            direction_regex=r"\bdebited\b",
        )
        unrelated = self.create_account(
            bank_name="Other Bank",
            account_number="9999",
        )
        payload = {
            "format": BACKUP_FORMAT,
            "version": BACKUP_VERSION,
            "accounts": [
                {
                    "bank_name": "Example Bank",
                    "account_number": "1234",
                    "actual_budget_account_name": "Restored Checking",
                    "actual_budget_account_id": "restored-account-id",
                    "actual_budget_payee_name": None,
                    "actual_budget_payee_id": None,
                    "is_salary_account": False,
                    "salary_amount": None,
                    "salary_tagname": None,
                    "email_parsing_rules": [
                        {
                            "direction": TransactionType.INCOMING,
                            "from_name": "alerts@example.com",
                            "subject": r"credited",
                            "direction_is_in": EmailElement.SUBJECT,
                            "direction_regex": r"restored credited",
                            "amount_is_in": EmailElement.BODY,
                            "amount_regex": r"restored amount",
                        },
                        {
                            "direction": TransactionType.OUTGOING,
                            "from_name": "new-alerts@example.com",
                            "subject": r"purchase",
                            "direction_is_in": EmailElement.SUBJECT,
                            "direction_regex": r"purchase",
                            "amount_is_in": EmailElement.BODY,
                            "amount_regex": r"USD\s*([\d.]+)",
                        },
                    ],
                }
            ],
        }

        response = self.client.post(
            reverse("admin:mailsync_bankaccount_backup_restore"),
            {"backup_file": self.backup_upload(payload)},
        )

        self.assertRedirects(
            response,
            reverse("admin:mailsync_bankaccount_changelist"),
        )
        account.refresh_from_db()
        self.assertEqual(account.actual_budget_account_name, "Restored Checking")
        self.assertEqual(account.actual_budget_account_id, "restored-account-id")
        self.assertFalse(account.is_salary_account)
        self.assertTrue(BankAccount.objects.filter(pk=unrelated.pk).exists())

        matching_rule.refresh_from_db()
        self.assertEqual(matching_rule.amount_regex, "restored amount")
        self.assertEqual(matching_rule.direction_regex, "restored credited")
        self.assertFalse(BankMailConfig.objects.filter(pk=stale_rule.pk).exists())
        self.assertEqual(account.bankmailconfig_set.count(), 2)
        self.assertTrue(
            account.bankmailconfig_set.filter(
                from_name="new-alerts@example.com",
                subject="purchase",
            ).exists()
        )

    def test_invalid_restore_rolls_back_all_changes(self):
        account = self.create_account()
        payload = {
            "format": BACKUP_FORMAT,
            "version": BACKUP_VERSION,
            "accounts": [
                {
                    "bank_name": "Example Bank",
                    "account_number": "1234",
                    "actual_budget_account_name": "Changed before failure",
                    "actual_budget_account_id": None,
                    "actual_budget_payee_name": None,
                    "actual_budget_payee_id": None,
                    "is_salary_account": False,
                    "salary_amount": None,
                    "salary_tagname": None,
                    "email_parsing_rules": [
                        {
                            "direction": "invalid-direction",
                            "from_name": "alerts@example.com",
                            "subject": "credited",
                            "direction_is_in": EmailElement.SUBJECT,
                            "direction_regex": "credited",
                            "amount_is_in": EmailElement.BODY,
                            "amount_regex": "amount",
                        }
                    ],
                }
            ],
        }

        response = self.client.post(
            reverse("admin:mailsync_bankaccount_backup_restore"),
            {"backup_file": self.backup_upload(payload)},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "is not a valid choice")
        account.refresh_from_db()
        self.assertEqual(account.actual_budget_account_name, "Checking")
        self.assertEqual(account.bankmailconfig_set.count(), 0)
