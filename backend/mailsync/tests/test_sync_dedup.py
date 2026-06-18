from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase

from ..builder import filter_synced
from ..data_models import TransactionType
from ..management.commands import utils
from .helpers import make_transaction


class HashIdentityTests(SimpleTestCase):
    def test_hash_is_independent_of_to_trx(self):
        # Sync identity must not change when consolidation pairs a transaction
        # into a transfer, otherwise it can re-sync once its counterpart leg
        # drops out of the fetch window.
        outgoing = make_transaction("out", transaction_type=TransactionType.OUTGOING)
        before = hash(outgoing)

        outgoing.to_trx = make_transaction("in")

        self.assertEqual(hash(outgoing), before)


class FilterSyncedTests(SimpleTestCase):
    @patch("mailsync.builder.SyncLog")
    def test_drops_synced_transaction_regardless_of_pairing(self, synclog_mock):
        outgoing = make_transaction("out", transaction_type=TransactionType.OUTGOING)
        synclog_mock.objects.filter.return_value.values_list.return_value = [
            str(hash(outgoing))
        ]

        # The stored hash predates pairing; pairing must not let it slip through.
        outgoing.to_trx = make_transaction("in")

        self.assertEqual(filter_synced([outgoing]), [])

    @patch("mailsync.builder.SyncLog")
    def test_keeps_unsynced_transaction(self, synclog_mock):
        outgoing = make_transaction("out", transaction_type=TransactionType.OUTGOING)
        synclog_mock.objects.filter.return_value.values_list.return_value = []

        self.assertEqual(filter_synced([outgoing]), [outgoing])


class TransferLoggingTests(SimpleTestCase):
    @patch("mailsync.management.commands.utils._make_sync_log")
    def test_transfer_logs_both_legs(self, make_log_mock):
        make_log_mock.return_value = MagicMock(success=True, error_message=None)
        outgoing = make_transaction("out", transaction_type=TransactionType.OUTGOING)
        incoming = make_transaction("in")
        outgoing.to_trx = incoming

        utils.log_sync_result(outgoing, {})

        logged = [c.args[0] for c in make_log_mock.call_args_list]
        self.assertIn(outgoing, logged)
        self.assertIn(incoming, logged)
        self.assertEqual(make_log_mock.return_value.save.call_count, 2)

    @patch("mailsync.management.commands.utils._make_sync_log")
    def test_non_transfer_logs_single_leg(self, make_log_mock):
        make_log_mock.return_value = MagicMock(success=True, error_message=None)
        incoming = make_transaction("in")

        utils.log_sync_result(incoming, {})

        self.assertEqual(make_log_mock.return_value.save.call_count, 1)
