from django.core.management.base import BaseCommand

from mailsync.builder import get_transactions
from mailsync.services.gmail import get_primary_unread_messages
from . import utils


class Command(BaseCommand):
    def handle(self, *args, **kwargs):
        messages = get_primary_unread_messages()
        transactions = get_transactions(messages)
        if len(transactions) == 0:
            return
        transactions = utils.filter_transactions(transactions)
        utils.set_ab_properties(transactions)
