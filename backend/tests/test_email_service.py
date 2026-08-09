import unittest
from unittest.mock import AsyncMock, patch

from app.core.config import settings
from app.services.email import EmailService


class EmailServiceTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.original_environment = settings.ENVIRONMENT
        self.original_use_credentials = settings.USE_CREDENTIALS

    def tearDown(self) -> None:
        settings.ENVIRONMENT = self.original_environment
        settings.USE_CREDENTIALS = self.original_use_credentials

    @patch("app.services.email.aiosmtplib.send", new_callable=AsyncMock)
    async def test_sends_html_email_with_configured_transport(self, smtp_send):
        settings.USE_CREDENTIALS = True

        await EmailService.send_email(
            "buyer@example.com",
            "Order received",
            "<strong>Thanks</strong>",
        )

        smtp_send.assert_awaited_once()
        message = smtp_send.await_args.args[0]
        options = smtp_send.await_args.kwargs
        self.assertEqual(message["To"], "buyer@example.com")
        self.assertEqual(message["Subject"], "Order received")
        self.assertEqual(
            message.get_body(preferencelist=("html",)).get_content().strip(),
            "<strong>Thanks</strong>",
        )
        self.assertEqual(options["hostname"], settings.MAIL_SERVER)
        self.assertEqual(options["username"], settings.MAIL_USERNAME)
        self.assertEqual(options["password"], settings.MAIL_PASSWORD)
        self.assertEqual(options["start_tls"], settings.MAIL_STARTTLS)
        self.assertEqual(options["use_tls"], settings.MAIL_SSL_TLS)
        self.assertTrue(options["validate_certs"])

    @patch("app.services.email.aiosmtplib.send", new_callable=AsyncMock)
    async def test_omits_credentials_when_disabled(self, smtp_send):
        settings.USE_CREDENTIALS = False

        await EmailService.send_email("buyer@example.com", "Subject", "<p>Body</p>")

        self.assertIsNone(smtp_send.await_args.kwargs["username"])
        self.assertIsNone(smtp_send.await_args.kwargs["password"])

    @patch("app.services.email.aiosmtplib.send", new_callable=AsyncMock)
    async def test_development_logs_provider_failure_without_breaking_flow(self, smtp_send):
        settings.ENVIRONMENT = "development"
        smtp_send.side_effect = RuntimeError("provider unavailable")

        await EmailService.send_email("buyer@example.com", "Subject", "<p>Body</p>")

    @patch("app.services.email.aiosmtplib.send", new_callable=AsyncMock)
    async def test_production_propagates_provider_failure(self, smtp_send):
        settings.ENVIRONMENT = "production"
        smtp_send.side_effect = RuntimeError("provider unavailable")

        with self.assertRaisesRegex(RuntimeError, "provider unavailable"):
            await EmailService.send_email("buyer@example.com", "Subject", "<p>Body</p>")


if __name__ == "__main__":
    unittest.main()
