import unittest

from cryptography.fernet import Fernet
from pydantic import ValidationError

from app.core.config import Settings


def production_settings(**overrides):
    values = {
        "POSTGRES_SERVER": "db",
        "POSTGRES_USER": "lumefy",
        "POSTGRES_PASSWORD": "database-password-for-tests",
        "POSTGRES_DB": "lumefy",
        "POSTGRES_PORT": "5432",
        "DATABASE_URL": "postgresql+asyncpg://lumefy:test@db:5432/lumefy",
        "SECRET_KEY": "application-secret-for-tests-1234567890",
        "CREDENTIAL_ENCRYPTION_KEY": Fernet.generate_key().decode("ascii"),
        "ENVIRONMENT": "production",
        "FIRST_SUPERUSER": "admin@example.com",
        "FIRST_SUPERUSER_PASSWORD": "administrator-password-for-tests",
        "MAIL_SERVER": "smtp.test.example.com",
        "MAIL_USERNAME": "delivery@test.example.com",
        "MAIL_PASSWORD": "smtp-password-for-tests",
        "MAIL_FROM": "no-reply@test.example.com",
    }
    values.update(overrides)
    return Settings(_env_file=None, **values)


class ProductionSettingsTests(unittest.TestCase):
    def test_accepts_independent_strong_production_secrets(self):
        configured = production_settings()

        self.assertEqual(configured.ENVIRONMENT, "production")

    def test_rejects_documentation_placeholders(self):
        with self.assertRaises(ValidationError):
            production_settings(SECRET_KEY="replace-with-a-long-random-secret")

    def test_rejects_conflicting_smtp_tls_modes_in_any_environment(self):
        with self.assertRaises(ValidationError):
            production_settings(MAIL_STARTTLS=True, MAIL_SSL_TLS=True)

    def test_rejects_placeholder_smtp_password_in_production(self):
        with self.assertRaises(ValidationError):
            production_settings(MAIL_PASSWORD="change-me")

    def test_rejects_unvalidated_smtp_certificates_in_production(self):
        with self.assertRaises(ValidationError):
            production_settings(VALIDATE_CERTS=False)


if __name__ == "__main__":
    unittest.main()
