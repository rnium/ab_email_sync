from django import forms


class BankAccountRestoreForm(forms.Form):
    backup_file = forms.FileField(
        label="Backup file",
        help_text="Select a JSON file exported from the Bank Accounts admin.",
        widget=forms.ClearableFileInput(attrs={"accept": "application/json,.json"}),
    )
