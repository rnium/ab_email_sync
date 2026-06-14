import os
from typing import Any

import requests
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

from mailsync.models import Configuration

# ---------------------------------------------------------------------------
# API server base URL – read from environment (same .env Django loads).
# Defaults to the api_server's default port.
# ---------------------------------------------------------------------------
_API_SERVER_URL = os.environ.get("ACTUAL_API_SERVER_URL", "http://localhost:3000")
_API_BASE = f"{_API_SERVER_URL}/api/v1"


# ---------------------------------------------------------------------------
# Endpoint specifications
# ---------------------------------------------------------------------------
ENDPOINT_ACCOUNTS = f"{_API_BASE}/accounts"
ENDPOINT_PAYEES = f"{_API_BASE}/payees"
ENDPOINT_CATEGORY_GROUPS = f"{_API_BASE}/category-groups"


def endpoint_import_transactions(account_id: str) -> str:
    return f"{_API_BASE}/accounts/{account_id}/transactions/import"


# ---------------------------------------------------------------------------
# Request caller utilities
# ---------------------------------------------------------------------------


def _actual_headers() -> dict[str, str]:
    keys = (
        settings.ACTUAL_BUDGET_PASSWORD_KEY,
        settings.ACTUAL_BUDGET_SYNC_ID_KEY,
    )
    configs = Configuration.objects.filter(key__in=keys).in_bulk(field_name="key")
    missing = [key for key in keys if not configs.get(key) or not configs[key].value]
    if missing:
        raise ImproperlyConfigured(
            f"Missing Actual Budget configuration value(s): {', '.join(missing)}"
        )

    return {
        "X-Actual-Password": configs[settings.ACTUAL_BUDGET_PASSWORD_KEY].value,
        "X-Actual-Sync-Id": configs[settings.ACTUAL_BUDGET_SYNC_ID_KEY].value,
    }


_TIMEOUT = 30


def api_get(url: str, params: dict | None = None) -> Any:
    """Perform a GET request and return the unwrapped ``data`` payload."""
    response = requests.get(url, params=params, headers=_actual_headers(), timeout=_TIMEOUT)
    response.raise_for_status()
    return response.json().get("data")


def api_post(url: str, body: Any) -> Any:
    """Perform a POST request with a JSON body and return the unwrapped ``data`` payload."""
    response = requests.post(url, json=body, headers=_actual_headers(), timeout=_TIMEOUT)
    response.raise_for_status()
    return response.json().get("data")
