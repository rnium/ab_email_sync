from django.contrib import admin

from .models import BankAccount, BankMailConfig, Configuration, SyncLog


@admin.register(Configuration)
class ConfigurationAdmin(admin.ModelAdmin):
    list_display = ("label", "is_value_set", "parent")
    search_fields = ("label", "value")
    fieldsets = (("Configuration", {"fields": ("value", "parent")}),)

    def get_readonly_fields(self, request, obj=None):
        if obj:
            return ("key", "label", "parent")
        return ("parent",)

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    @admin.display(description="Value set", boolean=True)
    def is_value_set(self, obj):
        return bool(obj.value and obj.value.strip())


class BankMailConfigInline(admin.TabularInline):
    model = BankMailConfig
    can_delete = True
    extra = 0
    show_change_link = True
    fields = (
        "direction",
        "from_name",
        "subject",
        "direction_is_in",
        "direction_regex",
        "amount_is_in",
        "amount_regex",
    )


@admin.register(BankAccount)
class BankAccountAdmin(admin.ModelAdmin):
    list_display = (
        "bank_name",
        "account_number",
        "actual_budget_account_name",
        "actual_budget_payee",
        "is_salary_account",
    )
    list_filter = ("bank_name", "is_salary_account")
    search_fields = (
        "bank_name",
        "account_number",
        "actual_budget_account_name",
        "actual_budget_payee_name",
    )
    inlines = (BankMailConfigInline,)
    fieldsets = (
        (
            "Bank account",
            {"fields": ("bank_name", "account_number")},
        ),
        (
            "Actual Budget mapping",
            {
                "fields": (
                    "actual_budget_account_name",
                    "actual_budget_payee_name",
                )
            },
        ),
        (
            "Salary handling",
            {
                "fields": (
                    "is_salary_account",
                    "salary_amount",
                    "salary_tagname",
                )
            },
        ),
    )

    @admin.display(description="Actual payee")
    def actual_budget_payee(self, obj):
        return obj.actual_budget_payee_name or obj.actual_budget_account_name


@admin.register(BankMailConfig)
class BankMailConfigAdmin(admin.ModelAdmin):
    list_display = (
        "bank_account",
        "direction",
        "from_name",
        "subject",
        "amount_is_in",
    )
    list_filter = (
        "direction",
        "amount_is_in",
        "direction_is_in",
        "bank_account__bank_name",
    )
    search_fields = (
        "bank_account__bank_name",
        "bank_account__account_number",
        "from_name",
        "subject",
        "direction_regex",
        "amount_regex",
    )
    autocomplete_fields = ("bank_account",)
    fieldsets = (
        (
            "Matching email",
            {"fields": ("bank_account", "from_name", "subject")},
        ),
        (
            "Transaction direction",
            {"fields": ("direction", "direction_is_in", "direction_regex")},
        ),
        (
            "Transaction amount",
            {"fields": ("amount_is_in", "amount_regex")},
        ),
    )


@admin.register(SyncLog)
class SyncLogAdmin(admin.ModelAdmin):
    list_display = (
        "sync_time",
        "success",
        "transaction_type",
        "transaction_amount",
        "bank_account",
        "transaction_hash",
    )
    list_filter = (
        "success",
        "transaction_type",
        "sync_time",
        "bank_mail__bank_account__bank_name",
    )
    search_fields = (
        "transaction_hash",
        "error_message",
        "bank_mail__from_name",
        "bank_mail__subject",
        "bank_mail__bank_account__bank_name",
        "bank_mail__bank_account__account_number",
    )
    readonly_fields = (
        "transaction_type",
        "transaction_amount",
        "bank_mail",
        "sync_time",
        "success",
        "error_message",
        "transaction_hash",
    )
    date_hierarchy = "sync_time"
    list_select_related = ("bank_mail", "bank_mail__bank_account")

    def has_add_permission(self, request):
        return False

    @admin.display(
        description="Bank account",
        ordering="bank_mail__bank_account__bank_name",
    )
    def bank_account(self, obj):
        return obj.bank_mail.bank_account
