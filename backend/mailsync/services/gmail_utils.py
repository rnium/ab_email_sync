import base64
from html import unescape
from html.parser import HTMLParser

class HTMLTextExtractor(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []

    def handle_data(self, data):
        self.parts.append(data)

    def handle_starttag(self, tag, attrs):
        if tag in {'br', 'p', 'div', 'li', 'tr', 'table', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6'}:
            self.parts.append('\n')

    def handle_endtag(self, tag):
        if tag in {'p', 'div', 'li', 'tr', 'table', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6'}:
            self.parts.append('\n')

    def get_text(self):
        return ''.join(self.parts).strip()


def html_to_text(html):
    extractor = HTMLTextExtractor()
    extractor.feed(html)
    return unescape(extractor.get_text())


def decode_body(body):
    encoded = body.get('data', '') or ''
    padded = encoded + '=' * (-len(encoded) % 4)
    return base64.urlsafe_b64decode(padded).decode('utf-8', errors='replace')


def get_message_body(payload):
    mime_type = payload.get('mimeType', '')
    if mime_type == 'text/plain':
        return decode_body(payload.get('body', {}))
    if mime_type == 'text/html':
        return html_to_text(decode_body(payload.get('body', {})))

    parts = payload.get('parts', []) or []
    # prefer plain text when available
    for part in parts:
        if part.get('mimeType') == 'text/plain':
            return decode_body(part.get('body', {}))
    for part in parts:
        if part.get('mimeType') == 'text/html':
            return html_to_text(decode_body(part.get('body', {})))
    for part in parts:
        body_text = get_message_body(part)
        if body_text:
            return body_text
    return ''