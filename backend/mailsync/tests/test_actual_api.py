from unittest.mock import Mock, patch

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.test import TestCase

from ..models import Configuration
from ..services.actual_utils import api_get, api_post


class ActualApiRequestTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        Configuration.objects.create(
            label="Actual Budget Password",
            key=settings.ACTUAL_BUDGET_PASSWORD_KEY,
            value="server-password",
        )
        Configuration.objects.create(
            label="Actual Budget Sync ID",
            key=settings.ACTUAL_BUDGET_SYNC_ID_KEY,
            value="budget-sync-id",
        )

    @staticmethod
    def response(data):
        response = Mock()
        response.json.return_value = {"data": data}
        return response

    @patch("mailsync.services.actual_utils.requests.get")
    def test_api_get_sends_credentials_from_configuration_values(self, get_mock):
        get_mock.return_value = self.response(["account"])

        result = api_get("http://api.test/accounts", params={"hidden": "false"})

        self.assertEqual(result, ["account"])
        get_mock.assert_called_once_with(
            "http://api.test/accounts",
            params={"hidden": "false"},
            headers={
                "X-Actual-Password": "server-password",
                "X-Actual-Sync-Id": "budget-sync-id",
            },
            timeout=30,
        )
        get_mock.return_value.raise_for_status.assert_called_once_with()

    @patch("mailsync.services.actual_utils.requests.post")
    def test_api_post_sends_credentials_from_configuration_values(self, post_mock):
        post_mock.return_value = self.response({"added": ["transaction-id"]})
        body = {"transactions": [{"amount": 10}]}

        result = api_post("http://api.test/import", body)

        self.assertEqual(result, {"added": ["transaction-id"]})
        post_mock.assert_called_once_with(
            "http://api.test/import",
            json=body,
            headers={
                "X-Actual-Password": "server-password",
                "X-Actual-Sync-Id": "budget-sync-id",
            },
            timeout=30,
        )
        post_mock.return_value.raise_for_status.assert_called_once_with()

    @patch("mailsync.services.actual_utils.requests.get")
    def test_api_request_rejects_blank_configuration_values(self, get_mock):
        Configuration.objects.filter(
            key=settings.ACTUAL_BUDGET_SYNC_ID_KEY
        ).update(value="")

        with self.assertRaisesMessage(
            ImproperlyConfigured,
            settings.ACTUAL_BUDGET_SYNC_ID_KEY,
        ):
            api_get("http://api.test/accounts")

        get_mock.assert_not_called()
