import base64
import re
from html import unescape
from html.parser import HTMLParser

# Known stub messages that senders insert as the plain-text part of HTML-only emails.
_HTML_PLACEHOLDER_PATTERNS = re.compile(
    r"(html.compatible|html.capable|html.enabled|view.this.email.in.your.browser"
    r"|view.the.message.please.use|enable.html|not.support.html|displayed.in.html"
    r"|best.viewed.in|click.here.to.view)",
    re.IGNORECASE,
)


def _is_html_placeholder(text: str) -> bool:
    """Return True if the plain-text part is just a stub telling the user to use an HTML viewer."""
    stripped = text.strip()
    if not stripped:
        return True
    return bool(_HTML_PLACEHOLDER_PATTERNS.search(stripped))


class HTMLTextExtractor(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []

    def handle_data(self, data):
        self.parts.append(data)

    def handle_starttag(self, tag, attrs):
        if tag in {
            "br",
            "p",
            "div",
            "li",
            "tr",
            "table",
            "h1",
            "h2",
            "h3",
            "h4",
            "h5",
            "h6",
        }:
            self.parts.append("\n")

    def handle_endtag(self, tag):
        if tag in {"p", "div", "li", "tr", "table", "h1", "h2", "h3", "h4", "h5", "h6"}:
            self.parts.append("\n")

    def get_text(self):
        return "".join(self.parts).strip()


def html_to_text(html: str) -> str:
    extractor = HTMLTextExtractor()
    extractor.feed(html)
    raw = unescape(extractor.get_text())
    # collapse runs of blank lines to a single blank line
    return re.sub(r"\n{3,}", "\n\n", raw).strip()


def decode_body(body: dict) -> str:
    encoded = body.get("data") or ""
    if not encoded:
        return ""
    padded = encoded + "=" * (-len(encoded) % 4)
    return base64.urlsafe_b64decode(padded).decode("utf-8", errors="replace")


def get_message_body(payload: dict) -> str:
    """
    Recursively extract plain-text content from a Gmail message payload.

    Priority order:
      1. text/plain  — unless it is an HTML-viewer placeholder stub
      2. text/html   — converted to plain text
      3. Recurse into multipart sub-parts (mixed, related, signed, …)
    """
    mime_type = payload.get("mimeType", "")

    # Leaf plain-text part
    if mime_type == "text/plain":
        return decode_body(payload.get("body", {}))

    # Leaf HTML part
    if mime_type == "text/html":
        return html_to_text(decode_body(payload.get("body", {})))

    parts = payload.get("parts") or []
    if not parts:
        return ""

    # For multipart/alternative: prefer plain text, but skip HTML-only placeholder stubs
    if mime_type == "multipart/alternative":
        plain_text = None
        html_text = None

        for part in parts:
            if part.get("mimeType") == "text/plain" and plain_text is None:
                plain_text = decode_body(part.get("body", {}))
            elif part.get("mimeType") == "text/html" and html_text is None:
                html_text = html_to_text(decode_body(part.get("body", {})))

        if plain_text and not _is_html_placeholder(plain_text):
            return plain_text
        if html_text and html_text.strip():
            return html_text
        # fall through to recursive search below

    # For all other multipart types (mixed, related, signed, …) recurse into sub-parts
    for part in parts:
        text = get_message_body(part)
        if text.strip():
            return text

    return ""
