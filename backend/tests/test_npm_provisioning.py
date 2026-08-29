import json
import unittest
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch
from uuid import uuid4

from app.api.v1.endpoints.storefront import verify_storefront_domain
from app.services.npm_provisioning import NginxProxyManagerClient, NpmApiError
from app.workers.domain_provisioning_worker import public_error_message, retry_delay_seconds


class FakeResponse:
    def __init__(self, status_code, payload=None, headers=None):
        self.status_code = status_code
        self._payload = payload
        self.headers = headers or {}
        self.content = b"" if payload is None else json.dumps(payload).encode("utf-8")
        self.text = "" if payload is None else json.dumps(payload)

    def json(self):
        return self._payload


class FakeSession:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def request(self, method, url, **kwargs):
        self.calls.append((method, url, kwargs))
        if not self.responses:
            raise AssertionError(f"Unexpected request: {method} {url}")
        return self.responses.pop(0)


def client_with_responses(*responses):
    session = FakeSession(responses)
    client = NginxProxyManagerClient(
        api_url="http://npm:81/api",
        identity="automation@example.com",
        password="strong-password",
        forward_scheme="http",
        forward_host="lumefy-storefront-1",
        forward_port=3000,
        session=session,
    )
    return client, session


class NpmProvisioningClientTests(unittest.TestCase):
    def test_creates_proxy_host_certificate_and_enables_ssl(self):
        client, session = client_with_responses(
            FakeResponse(200, {"token": "jwt"}),
            FakeResponse(200, []),
            FakeResponse(201, {"id": 12, "certificate_id": 0}),
            FakeResponse(200, {"shop.example.com": "ok"}),
            FakeResponse(200, []),
            FakeResponse(201, {"id": 33}),
            FakeResponse(200, {"id": 12}),
        )

        result = client.provision_domain("shop.example.com")

        self.assertEqual(result.proxy_host_id, 12)
        self.assertEqual(result.certificate_id, 33)
        certificate_calls = [call for call in session.calls if call[1].endswith("/nginx/certificates")]
        self.assertEqual(len(certificate_calls), 2)
        update_payload = session.calls[-1][2]["json"]
        self.assertTrue(update_payload["ssl_forced"])
        self.assertEqual(update_payload["certificate_id"], 33)

    def test_reuses_an_existing_managed_host_and_certificate(self):
        client, session = client_with_responses(
            FakeResponse(200, {"token": "jwt"}),
            FakeResponse(200, [{
                "id": 12,
                "domain_names": ["shop.example.com"],
                "forward_scheme": "http",
                "forward_host": "lumefy-storefront-1",
                "forward_port": 3000,
                "certificate_id": 33,
            }]),
            FakeResponse(200, {"shop.example.com": "ok"}),
            FakeResponse(200, {"id": 12}),
        )

        result = client.provision_domain("SHOP.EXAMPLE.COM.")

        self.assertEqual(result.certificate_id, 33)
        self.assertFalse(any(call[0] == "POST" and call[1].endswith("/nginx/certificates") for call in session.calls))

    def test_rejects_a_shared_or_foreign_proxy_host(self):
        client, _session = client_with_responses(
            FakeResponse(200, {"token": "jwt"}),
            FakeResponse(200, [{
                "id": 5,
                "domain_names": ["shop.example.com", "*.jaofy.com"],
                "forward_scheme": "http",
                "forward_host": "lumefy-storefront-1",
                "forward_port": 3000,
                "certificate_id": 0,
            }]),
        )

        with self.assertRaises(NpmApiError) as raised:
            client.provision_domain("shop.example.com")

        self.assertFalse(raised.exception.retryable)
        self.assertEqual(raised.exception.status_code, 409)

    def test_stops_before_certificate_request_when_http_is_not_ready(self):
        client, session = client_with_responses(
            FakeResponse(200, {"token": "jwt"}),
            FakeResponse(200, [{
                "id": 12,
                "domain_names": ["shop.example.com"],
                "forward_scheme": "http",
                "forward_host": "lumefy-storefront-1",
                "forward_port": 3000,
                "certificate_id": 0,
            }]),
            FakeResponse(200, {"shop.example.com": "404"}),
        )

        with self.assertRaises(NpmApiError) as raised:
            client.provision_domain("shop.example.com")

        self.assertTrue(raised.exception.retryable)
        self.assertFalse(any(call[1].endswith("/nginx/certificates") for call in session.calls))

    def test_retry_schedule_respects_provider_retry_after(self):
        self.assertEqual(retry_delay_seconds(1), 300)
        self.assertEqual(retry_delay_seconds(2), 900)
        self.assertEqual(retry_delay_seconds(3), 3600)
        self.assertEqual(retry_delay_seconds(1, 1200), 1200)

    def test_internal_npm_auth_error_is_not_exposed_to_merchants(self):
        message = public_error_message(
            NpmApiError("Invalid password for automation@example.com", retryable=False, status_code=401)
        )

        self.assertNotIn("automation@example.com", message)
        self.assertIn("administrador", message)


class StorefrontDomainProvisioningTests(unittest.IsolatedAsyncioTestCase):
    async def test_successful_txt_verification_queues_npm_provisioning(self):
        now = datetime.now(timezone.utc)
        domain = SimpleNamespace(
            id=uuid4(),
            storefront_id=uuid4(),
            domain="shop.example.com",
            is_primary=True,
            is_verified=False,
            verification_token="token",
            verified_at=None,
            provisioning_status="PENDING_VERIFICATION",
            provisioning_attempts=0,
            provisioning_error=None,
            provisioning_next_attempt_at=None,
            provisioning_last_attempt_at=None,
            npm_proxy_host_id=None,
            npm_certificate_id=None,
            provisioned_at=None,
            company_id=uuid4(),
            created_at=now,
            updated_at=now,
            is_active=True,
            updated_by_id=None,
        )
        db = SimpleNamespace(
            scalar=AsyncMock(return_value=domain),
            add=Mock(),
            commit=AsyncMock(),
            refresh=AsyncMock(),
        )
        user = SimpleNamespace(id=uuid4(), company_id=domain.company_id)

        with (
            patch(
                "app.api.v1.endpoints.storefront._verify_domain_txt_record",
                new=AsyncMock(return_value=True),
            ),
            patch("app.api.v1.endpoints.storefront.settings.NPM_PROVISIONING_ENABLED", True),
        ):
            serialized = await verify_storefront_domain(
                db=db,
                domain_id=domain.id,
                current_user=user,
            )

        self.assertTrue(serialized.is_verified)
        self.assertEqual(serialized.provisioning_status, "QUEUED")
        self.assertIsNotNone(serialized.provisioning_next_attempt_at)
        db.commit.assert_awaited_once()


if __name__ == "__main__":
    unittest.main()
