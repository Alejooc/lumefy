import socket
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from app.core.config import settings
from app.services.integration_service import (
    IntegrationRequestError,
    _asset_url_matches_source,
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
        return SimpleNamespace(source_type="REST", base_url=base_url)

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

    def test_asset_proxy_requires_matching_origin_and_base_path(self):
        source = SimpleNamespace(
            base_url="https://panel.example/api/external",
            configuration={"asset_base_url": "https://panel.example/api/external"},
        )

        self.assertTrue(_asset_url_matches_source(source, "https://panel.example/api/external/products/1/a.jpg"))
        self.assertFalse(_asset_url_matches_source(source, "https://panel.example/other/products/1/a.jpg"))
        self.assertFalse(_asset_url_matches_source(source, "https://other.example/api/external/products/1/a.jpg"))


if __name__ == "__main__":
    unittest.main()
