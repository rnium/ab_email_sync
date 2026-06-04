from django.db import models

class Configuration(models.Model):
    label = models.CharField(max_length=255)
    key = models.CharField(max_length=255, unique=True)
    value = models.TextField()
    
    def __str__(self):
        return f"{self.label} ({self.key})"

class BankAccount(models.Model):
    bank_name = models.CharField(max_length=255)
    account_number = models.CharField(max_length=20)
    actual_budget_account_name = models.CharField(max_length=255)
    actual_budget_payee_name = models.CharField(max_length=255, null=True, blank=True) # If payee name is not provided, use actual budget account name as payee name
    is_salary_account = models.BooleanField(default=False)
    salary_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    salary_tagname = models.CharField(max_length=255, null=True, blank=True)
    
    def __str__(self):
        return f"{self.bank_name} - {self.account_number}"


class BankMail(models.Model):
    bank_account = models.ForeignKey(BankAccount, on_delete=models.CASCADE)
    from_name = models.CharField(max_length=255)
    subject = models.CharField(max_length=255)
    amount_regex = models.CharField(max_length=255)
    
    def __str__(self):
        return f"[{self.from_name}] {self.subject}"


class SyncLog(models.Model):
    transaction_types = (
        ('transfer', 'Transfer'),
        ('deposit', 'Deposit'),
        ('withdrawal', 'Withdrawal'),
    )
    
    transaction_type = models.CharField(max_length=20, choices=transaction_types)
    transaction_amount = models.DecimalField(max_digits=10, decimal_places=2)
    bank_mail = models.ForeignKey(BankMail, on_delete=models.CASCADE)
    sync_time = models.DateTimeField(auto_now_add=True)
    success = models.BooleanField(default=False)
    error_message = models.TextField(null=True, blank=True)
    transaction_hash = models.CharField(max_length=255, null=True, blank=True, db_index=True)
    
    class Meta:
        ordering = ['-sync_time']