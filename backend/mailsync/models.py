from django.db import models
from .data_models import TransactionType, EmailElement


class Configuration(models.Model):
    label = models.CharField(max_length=255)
    key = models.CharField(max_length=255, unique=True)
    value = models.TextField()

    class Meta:
        verbose_name = "system configuration"
        verbose_name_plural = "system configuration"
        ordering = ["label"]

    def __str__(self):
        return f"{self.label} ({self.key})"


class BankAccount(models.Model):
    bank_name = models.CharField(max_length=255)
    account_number = models.CharField(max_length=20)
    actual_budget_account_name = models.CharField(max_length=255)
    actual_budget_payee_name = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        help_text="Leave blank to use the Actual Budget account name as the payee.",
    )
    is_salary_account = models.BooleanField(default=False)
    salary_amount = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )
    salary_tagname = models.CharField(max_length=255, null=True, blank=True)

    class Meta:
        verbose_name = "bank account"
        verbose_name_plural = "bank accounts"
        ordering = ["bank_name", "account_number"]

    def __str__(self):
        return f"{self.bank_name} - {self.account_number}"


class BankMailConfig(models.Model):
    mail_element_choices = [
        (item.value, item.name.title()) for item in EmailElement
    ]
    direction_choices = (
        (item.value, item.name.title()) for item in TransactionType
    )
    direction = models.CharField(max_length=20, choices=direction_choices)
    bank_account = models.ForeignKey(BankAccount, on_delete=models.CASCADE)
    from_name = models.CharField(max_length=255)
    subject = models.CharField(max_length=255, verbose_name="Subject Regex")
    direction_is_in = models.CharField(
        max_length=255, choices=mail_element_choices, default="subject"
    )
    direction_regex = models.CharField(max_length=500)
    amount_is_in = models.CharField(
        max_length=255, choices=mail_element_choices, default="body"
    )
    amount_regex = models.CharField(max_length=255)

    class Meta:
        verbose_name = "email parsing rule"
        verbose_name_plural = "email parsing rules"
        ordering = ["bank_account__bank_name", "direction", "from_name"]

    def __str__(self):
        return f"{self.bank_account} | {self.direction} | {self.from_name}"


class SyncLog(models.Model):
    transaction_types = (
        ("transfer", "Transfer"),
        ("deposit", "Deposit"),
        ("withdrawal", "Withdrawal"),
    )

    transaction_type = models.CharField(max_length=20, choices=transaction_types)
    transaction_amount = models.DecimalField(max_digits=10, decimal_places=2)
    bank_mail = models.ForeignKey(BankMailConfig, on_delete=models.CASCADE)
    sync_time = models.DateTimeField(auto_now_add=True)
    success = models.BooleanField(default=False)
    error_message = models.TextField(null=True, blank=True)
    transaction_hash = models.CharField(
        max_length=255, null=True, blank=True, db_index=True
    )

    class Meta:
        verbose_name = "sync log"
        verbose_name_plural = "sync logs"
        ordering = ["-sync_time"]

    def __str__(self):
        status = "synced" if self.success else "failed"
        return f"{status}: {self.transaction_type} {self.transaction_amount} at {self.sync_time:%Y-%m-%d %H:%M}"
