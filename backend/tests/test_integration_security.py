import socket
import unittest
from io import BytesIO
from types import SimpleNamespace
from unittest.mock import Mock, patch
from urllib import error as urlerror

from app.core.config import settings
from app.services.integration_service import (
    IntegrationRequestError,
    _asset_url_matches_source,
    _preflight_auth,
    _request_json_sync,
    _url_for,
    validate_source,
)


class IntegrationSecurityTests(unittest.TestCase):
    def setUp(self) -> None:
        self.original_private_network_setting = settings.INTEGRATION_ALLOW_PRIVATE_NETWORKS
        settings.INTEGRATION_ALLOW_PRIVATE_NETWORKS = False

    def tearDown(self) -> None:
        settings.INTEGRATION_ALLOW_PRIVATE_NETWORKS = self.original_private_network_setting

    @staticmethod
    def source(base_url: str = "https://supplier.example") -> SimpleNamespace:
        return SimpleNamespace(source_type="REST", base_url=base_url, auth_type="none", credentials={})

    @patch("app.services.integration_service.socket.getaddrinfo")
    def test_public_source_is_accepted(self, getaddrinfo):
        getaddrinfo.return_value = [
            (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", 443)),
        ]

        validate_source(self.source())

    @patch("app.services.integration_service.socket.getaddrinfo")
    def test_private_and_loopback_sources_are_rejected(self, getaddrinfo):
        for address in ("127.0.0.1", "10.0.0.8", "169.254.169.254", "::1"):
            getaddrinfo.return_value = [
                (socket.AF_INET6 if ":" in address else socket.AF_INET, socket.SOCK_STREAM, 6, "", (address, 443)),
            ]
            with self.subTest(address=address), self.assertRaises(IntegrationRequestError):
                validate_source(self.source())

    def test_endpoint_cannot_escape_to_another_host(self):
        with self.assertRaises(IntegrationRequestError):
            _url_for(self.source(), "https://internal.example/admin")

    def test_url_embedded_credentials_are_rejected(self):
        with self.assertRaises(IntegrationRequestError):
            validate_source(self.source("https://user:secret@supplier.example"))

    def test_preflight_checks_auth_shape_without_exposing_secrets(self):
        missing = self.source()
        missing.auth_type = "bearer"
        missing.credentials = {}
        self.assertEqual(_preflight_auth(missing), (False, "Falta el token Bearer."))

        configured = self.source()
        configured.auth_type = "bearer"
        configured.credentials = {"token": "secret"}
        self.assertEqual(_preflight_auth(configured), (True, "Token Bearer configurado."))

        custom = self.source()
        custom.auth_type = "custom_headers"
        custom.credentials = {"headers": {"X-Provider": "configured"}}
        self.assertEqual(_preflight_auth(custom), (True, "Encabezados personalizados configurados."))

    def test_asset_proxy_requires_matching_origin_and_base_path(self):
        source = SimpleNamespace(
            base_url="https://panel.example/api/external",
            configuration={"asset_base_url": "https://panel.example/api/external"},
        )

        self.assertTrue(_asset_url_matches_source(source, "https://panel.example/api/external/products/1/a.jpg"))
        self.assertFalse(_asset_url_matches_source(source, "https://panel.example/other/products/1/a.jpg"))
        self.assertFalse(_asset_url_matches_source(source, "https://other.example/api/external/products/1/a.jpg"))

    @patch("app.services.integration_service.time.sleep")
    @patch("app.services.integration_service.urlrequest.build_opener")
    @patch("app.services.integration_service._validate_outbound_url")
    def test_json_request_retries_transient_provider_errors(self, validate_url, build_opener, sleep):
        class Response:
            headers = {"Content-Length": "12"}

            def getcode(self):
                return 200

            def read(self, limit=None):
                return b'{"data": []}'

            def __enter__(self):
                return self

            def __exit__(self, *args):
                return None

        response = Response()
        transient = urlerror.HTTPError(
            "https://supplier.example/products",
            503,
            "unavailable",
            {"Retry-After": "0"},
            BytesIO(b"temporary"),
        )
        opener = SimpleNamespace(open=Mock(side_effect=[transient, response]))
        build_opener.return_value = opener

        with patch.object(settings, "INTEGRATION_RETRY_ATTEMPTS", 1):
            status, payload = _request_json_sync("https://supplier.example/products", {})

        self.assertEqual(status, 200)
        self.assertEqual(payload, {"data": []})
        self.assertEqual(opener.open.call_count, 2)
        sleep.assert_called_once_with(0.0)

    @patch("app.services.integration_service.urlrequest.build_opener")
    @patch("app.services.integration_service._validate_outbound_url")
    def test_json_request_rejects_oversized_payload(self, validate_url, build_opener):
        class Response:
            headers = {"Content-Length": "5"}

            def getcode(self):
                return 200

            def read(self, limit=None):
                return b"large"

            def __enter__(self):
                return self

            def __exit__(self, *args):
                return None

        response = Response()
        build_opener.return_value = SimpleNamespace(open=Mock(return_value=response))

        with patch.object(settings, "INTEGRATION_MAX_RESPONSE_BYTES", 4), self.assertRaises(IntegrationRequestError) as error:
            _request_json_sync("https://supplier.example/products", {})

        self.assertEqual(error.exception.status_code, 413)


if __name__ == "__main__":
    unittest.main()
