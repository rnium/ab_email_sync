import base64
from types import SimpleNamespace
from unittest.mock import call, patch

from django.test import SimpleTestCase, TestCase

from .builder import (
    amount_str_to_float,
    build_transaction,
    consolidate_transactions,
    deduce_amount,
    deduce_transaction_type,
)
from .data_models import EmailElement, EmailMessage, Transaction, TransactionType
from .models import BankAccount, BankMailConfig
from .services.gmail_utils import decode_body, get_message_body, html_to_text
from .utils import get_transactions


def make_message(
    *,
    subject="Card credited",
    sender="alerts@example.com",
    date_str="2026-06-06",
    text="Amount: BDT 1,234.50",
):
    return EmailMessage(
        subject=subject,
        sender=sender,
        date_str=date_str,
        text=text,
        snippet="",
    )


def make_transaction(
    subject,
    *,
    amount=1.0,
    transaction_type=TransactionType.INCOMING,
):
    return Transaction(
        from_name="alerts@example.com",
        subject=subject,
        date="2026-06-06",
        amount=amount,
        transaction_type=transaction_type,
    )


def encoded_body(text):
    data = base64.urlsafe_b64encode(text.encode()).decode().rstrip("=")
    return {"data": data}


class BuilderParsingTests(SimpleTestCase):
    def test_deduce_transaction_type_uses_configured_element_case_insensitively(self):
        cases = [
            (
                SimpleNamespace(
                    direction_is_in=EmailElement.SUBJECT,
                    direction_regex=r"\bCREDITED\b",
                    direction=TransactionType.INCOMING,
                ),
                make_message(),
                TransactionType.INCOMING,
            ),
            (
                SimpleNamespace(
                    direction_is_in=EmailElement.BODY,
                    direction_regex=r"\bdebited\b",
                    direction=TransactionType.OUTGOING,
                ),
                make_message(text="Your account was DEBITED"),
                TransactionType.OUTGOING,
            ),
        ]

        for conf, message, expected in cases:
            with self.subTest(element=conf.direction_is_in):
                self.assertEqual(deduce_transaction_type(conf, message), expected)

    def test_deduce_transaction_type_returns_none_without_matching_content(self):
        conf = SimpleNamespace(
            direction_is_in=EmailElement.SUBJECT,
            direction_regex=r"credited",
            direction=TransactionType.INCOMING,
        )

        for subject in ("", "Card debited"):
            with self.subTest(subject=subject):
                self.assertIsNone(
                    deduce_transaction_type(conf, make_message(subject=subject))
                )

    def test_amount_str_to_float_handles_formatted_and_invalid_values(self):
        cases = {
            "1,234,567.89": 1234567.89,
            " 42 ": 42.0,
            "0": 0.0,
            "not-an-amount": None,
            "": None,
        }

        for value, expected in cases.items():
            with self.subTest(value=value):
                self.assertEqual(amount_str_to_float(value), expected)

    def test_deduce_amount_extracts_from_the_configured_element(self):
        cases = [
            (
                SimpleNamespace(
                    amount_is_in=EmailElement.BODY,
                    amount_regex=r"amount:\s*BDT\s*([\d,]+\.\d{2})",
                ),
                make_message(),
                1234.5,
            ),
            (
                SimpleNamespace(
                    amount_is_in=EmailElement.SUBJECT,
                    amount_regex=r"USD\s*([\d.]+)",
                ),
                make_message(subject="Purchase of USD 50.25"),
                50.25,
            ),
        ]

        for conf, message, expected in cases:
            with self.subTest(element=conf.amount_is_in):
                self.assertEqual(deduce_amount(conf, message), expected)

    def test_deduce_amount_returns_none_when_content_cannot_produce_an_amount(self):
        cases = [
            (
                SimpleNamespace(
                    amount_is_in=EmailElement.BODY,
                    amount_regex=r"BDT\s*([\d,]+)",
                ),
                make_message(text=""),
            ),
            (
                SimpleNamespace(
                    amount_is_in=EmailElement.BODY,
                    amount_regex=r"USD\s*([\d,]+)",
                ),
                make_message(),
            ),
            (
                SimpleNamespace(
                    amount_is_in=EmailElement.BODY,
                    amount_regex=r"Amount:\s*(\S+)",
                ),
                make_message(text="Amount: unavailable"),
            ),
        ]

        for conf, message in cases:
            with self.subTest(text=message.text, regex=conf.amount_regex):
                self.assertIsNone(deduce_amount(conf, message))


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


class BuildTransactionTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.account = BankAccount.objects.create(
            bank_name="Example Bank",
            account_number="1234",
            actual_budget_account_name="Checking",
        )

    def create_config(self, **overrides):
        values = {
            "bank_account": self.account,
            "from_name": "alerts@example.com",
            "subject": r"card credited",
            "direction": TransactionType.INCOMING,
            "direction_is_in": EmailElement.SUBJECT,
            "direction_regex": r"credited",
            "amount_is_in": EmailElement.BODY,
            "amount_regex": r"BDT\s*([\d,]+\.\d{2})",
        }
        values.update(overrides)
        return BankMailConfig.objects.create(**values)

    def test_build_transaction_selects_matching_config_and_maps_message_fields(self):
        self.create_config(subject=r"unrelated subject")
        self.create_config(
            subject=r"CARD CREDITED",
            direction=TransactionType.OUTGOING,
            direction_regex=r"CREDITED",
        )
        message = make_message()

        transaction = build_transaction(message)

        self.assertIsNotNone(transaction)
        self.assertEqual(transaction.from_name, message.sender)
        self.assertEqual(transaction.subject, message.subject)
        self.assertEqual(transaction.date, message.date_str)
        self.assertEqual(transaction.transaction_type, TransactionType.OUTGOING)
        self.assertEqual(transaction.amount, 1234.5)

    def test_build_transaction_returns_none_when_no_config_applies(self):
        self.assertIsNone(build_transaction(make_message()))

        self.create_config(from_name="other@example.com")
        self.create_config(subject=r"debit notification")

        self.assertIsNone(build_transaction(make_message()))

    def test_build_transaction_returns_none_when_required_data_is_not_extracted(self):
        self.create_config(amount_regex=r"USD\s*([\d.]+)")

        self.assertIsNone(build_transaction(make_message()))


class TransactionUtilsTests(SimpleTestCase):
    @patch("mailsync.utils.consolidate_transactions")
    @patch("mailsync.utils.build_transaction")
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


class GmailUtilsTests(SimpleTestCase):
    def test_html_to_text_preserves_readable_breaks_and_decodes_entities(self):
        html = "<p>Hello &amp; <strong>world</strong><br>Next line</p>"

        self.assertEqual(html_to_text(html), "Hello & world\nNext line")

    def test_decode_body_accepts_unpadded_urlsafe_data_and_replaces_invalid_utf8(self):
        self.assertEqual(decode_body(encoded_body("Amount: ৳50")), "Amount: ৳50")

        invalid_utf8 = base64.urlsafe_b64encode(b"\xff").decode().rstrip("=")
        self.assertEqual(decode_body({"data": invalid_utf8}), "\ufffd")

    def test_decode_body_returns_empty_text_when_data_is_missing(self):
        self.assertEqual(decode_body({}), "")

    def test_get_message_body_decodes_direct_plain_and_html_parts(self):
        cases = [
            (
                {"mimeType": "text/plain", "body": encoded_body("Plain text")},
                "Plain text",
            ),
            (
                {
                    "mimeType": "text/html",
                    "body": encoded_body("<p>HTML &amp; text</p>"),
                },
                "HTML & text",
            ),
        ]

        for payload, expected in cases:
            with self.subTest(mime_type=payload["mimeType"]):
                self.assertEqual(get_message_body(payload), expected)

    def test_get_message_body_prefers_plain_text_regardless_of_part_order(self):
        payload = {
            "mimeType": "multipart/alternative",
            "parts": [
                {"mimeType": "text/html", "body": encoded_body("<p>HTML</p>")},
                {"mimeType": "text/plain", "body": encoded_body("Plain")},
            ],
        }

        self.assertEqual(get_message_body(payload), "Plain")

    def test_get_message_body_recurses_into_nested_multipart_content(self):
        payload = {
            "mimeType": "multipart/mixed",
            "parts": [
                {
                    "mimeType": "application/pdf",
                    "body": encoded_body("ignored attachment"),
                },
                {
                    "mimeType": "multipart/alternative",
                    "parts": [
                        {
                            "mimeType": "text/plain",
                            "body": encoded_body("Nested plain text"),
                        }
                    ],
                },
            ],
        }

        self.assertEqual(get_message_body(payload), "Nested plain text")

    def test_get_message_body_returns_empty_text_when_no_readable_part_exists(self):
        payload = {
            "mimeType": "multipart/mixed",
            "parts": [{"mimeType": "application/pdf", "body": {}}],
        }

        self.assertEqual(get_message_body(payload), "")
