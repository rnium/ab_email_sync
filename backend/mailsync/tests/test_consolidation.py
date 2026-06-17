from django.test import SimpleTestCase

from ..builder import consolidate_transactions
from ..data_models import TransactionType
from .helpers import make_transaction


class ConsolidateTransactionTests(SimpleTestCase):
    def test_returns_original_list_when_consolidation_is_not_possible(self):
        cases = [
            [],
            [make_transaction("only")],
            [make_transaction("first"), make_transaction("second")],
        ]

        for transactions in cases:
            with self.subTest(transaction_count=len(transactions)):
                self.assertIs(consolidate_transactions(transactions), transactions)

    def test_links_matching_transactions_and_removes_incoming_transaction(self):
        incoming = make_transaction("incoming", amount=125.5)
        outgoing = make_transaction(
            "outgoing",
            amount=125.5,
            transaction_type=TransactionType.OUTGOING,
        )

        result = consolidate_transactions([incoming, outgoing])

        self.assertEqual(result, [outgoing])
        self.assertIs(outgoing.to_trx, incoming)

    def test_preserves_unmatched_transactions_and_their_order(self):
        unmatched_incoming = make_transaction("unmatched incoming", amount=50.0)
        outgoing = make_transaction(
            "outgoing",
            amount=125.5,
            transaction_type=TransactionType.OUTGOING,
        )
        matching_incoming = make_transaction("matching incoming", amount=125.5)
        unmatched_outgoing = make_transaction(
            "unmatched outgoing",
            amount=75.0,
            transaction_type=TransactionType.OUTGOING,
        )

        result = consolidate_transactions(
            [
                unmatched_incoming,
                outgoing,
                matching_incoming,
                unmatched_outgoing,
            ]
        )

        self.assertEqual(
            result,
            [unmatched_incoming, outgoing, unmatched_outgoing],
        )
        self.assertIs(outgoing.to_trx, matching_incoming)
        self.assertIsNone(unmatched_outgoing.to_trx)

    def test_uses_first_matching_incoming_transaction(self):
        first_incoming = make_transaction("first incoming", amount=125.5)
        second_incoming = make_transaction("second incoming", amount=125.5)
        outgoing = make_transaction(
            "outgoing",
            amount=125.5,
            transaction_type=TransactionType.OUTGOING,
        )

        result = consolidate_transactions(
            [first_incoming, second_incoming, outgoing]
        )

        self.assertEqual(result, [second_incoming, outgoing])
        self.assertIs(outgoing.to_trx, first_incoming)
