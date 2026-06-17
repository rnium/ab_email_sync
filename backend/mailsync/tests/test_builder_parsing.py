from types import SimpleNamespace

from django.test import SimpleTestCase

from ..builder import amount_str_to_float, deduce_amount, deduce_transaction_type
from ..data_models import EmailElement, TransactionType
from .helpers import make_message


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
