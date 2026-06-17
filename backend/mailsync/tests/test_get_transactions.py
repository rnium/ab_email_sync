from unittest.mock import call, patch

from django.test import SimpleTestCase

from ..builder import get_transactions
from .helpers import make_message, make_transaction


class TransactionUtilsTests(SimpleTestCase):
    @patch("mailsync.builder.consolidate_transactions")
    @patch("mailsync.builder.build_transaction")
    def test_get_transactions_filters_failed_builds_before_consolidating(
        self, build_mock, consolidate_mock
    ):
        messages = [
            make_message(subject="first"),
            make_message(subject="ignored"),
            make_message(subject="second"),
        ]
        first = make_transaction("first")
        second = make_transaction("second")
        build_mock.side_effect = [first, None, second]
        consolidated = [second, first]
        consolidate_mock.return_value = consolidated

        result = get_transactions(messages)

        self.assertIs(result, consolidated)
        self.assertEqual(
            build_mock.call_args_list,
            [call(message) for message in messages],
        )
        consolidate_mock.assert_called_once_with([first, second])
