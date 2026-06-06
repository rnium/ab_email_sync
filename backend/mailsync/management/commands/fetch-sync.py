from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.core.exceptions import ObjectDoesNotExist
from django.db import IntegrityError
from mailsync.services.gmail import get_primary_unread_messages


class Command(BaseCommand):
    def handle(self, *args, **kwargs):
        messages = get_primary_unread_messages()
        