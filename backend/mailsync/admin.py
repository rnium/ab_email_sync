from datetime import datetime

from django.contrib import admin
from django.contrib import messages
from django.core.exceptions import PermissionDenied, ValidationError
from django.http import HttpResponse
from django.shortcuts import redirect
from django.template.response import TemplateResponse
from django.urls import path, reverse

from .bank_account_backup import (
    decode_backup,
    encode_backup,
    export_bank_accounts,
    restore_bank_accounts,
)
from .forms import BankAccountRestoreForm
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
    change_list_template = "admin/mailsync/bankaccount/change_list.html"
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

    def changelist_view(self, request, extra_context=None):
        extra_context = {
            **(extra_context or {}),
            "can_restore_backup": self.has_restore_permission(request),
        }
        return super().changelist_view(request, extra_context)

    def has_restore_permission(self, request):
        rule_admin = self.admin_site.get_model_admin(BankMailConfig)
        return all(
            (
                self.has_view_permission(request),
                self.has_add_permission(request),
                self.has_change_permission(request),
                self.has_delete_permission(request),
                rule_admin.has_add_permission(request),
                rule_admin.has_change_permission(request),
                rule_admin.has_delete_permission(request),
            )
        )

    def get_urls(self):
        custom_urls = [
            path(
                "backup/export/",
                self.admin_site.admin_view(self.export_backup_view),
                name="mailsync_bankaccount_backup_export",
            ),
            path(
                "backup/restore/",
                self.admin_site.admin_view(self.restore_backup_view),
                name="mailsync_bankaccount_backup_restore",
            ),
        ]
        return custom_urls + super().get_urls()

    def export_backup_view(self, request):
        if not self.has_view_permission(request):
            raise PermissionDenied

        filename = f"bank-accounts-{datetime.now():%Y%m%d-%H%M%S}.json"
        response = HttpResponse(
            encode_backup(export_bank_accounts()),
            content_type="application/json",
        )
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response

    def restore_backup_view(self, request):
        if not self.has_restore_permission(request):
            raise PermissionDenied

        form = BankAccountRestoreForm(request.POST or None, request.FILES or None)
        if request.method == "POST" and form.is_valid():
            try:
                payload = decode_backup(form.cleaned_data["backup_file"])
                counts = restore_bank_accounts(payload)
            except ValidationError as error:
                form.add_error(None, ValidationError(error.messages))
            else:
                self.message_user(
                    request,
                    (
                        "Backup restored: "
                        f"{counts['accounts_created']} account(s) created, "
                        f"{counts['accounts_updated']} updated; "
                        f"{counts['rules_created']} rule(s) created, "
                        f"{counts['rules_updated']} updated, "
                        f"{counts['rules_deleted']} deleted."
                    ),
                    messages.SUCCESS,
                )
                return redirect(reverse("admin:mailsync_bankaccount_changelist"))

        context = {
            **self.admin_site.each_context(request),
            "opts": self.model._meta,
            "title": "Restore bank account backup",
            "form": form,
        }
        return TemplateResponse(
            request,
            "admin/mailsync/bankaccount/restore_backup.html",
            context,
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
