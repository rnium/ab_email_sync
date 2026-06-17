import base64

from django.test import SimpleTestCase

from ..services.gmail_utils import decode_body, get_message_body, html_to_text
from .helpers import encoded_body


class GmailUtilsTests(SimpleTestCase):
    def test_html_to_text_preserves_readable_breaks_and_decodes_entities(self):
        html = "<p>Hello &amp; <strong>world</strong><br>Next line</p>"

        self.assertEqual(html_to_text(html), "Hello & world\nNext line")

    def test_decode_body_accepts_unpadded_urlsafe_data_and_replaces_invalid_utf8(self):
        self.assertEqual(decode_body(encoded_body("Amount: ৳50")), "Amount: ৳50")

        invalid_utf8 = base64.urlsafe_b64encode(b"\xff").decode().rstrip("=")
        self.assertEqual(decode_body({"data": invalid_utf8}), "�")

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
