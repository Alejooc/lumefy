import unittest

from cryptography.fernet import Fernet

from app.core.config import settings
from app.core.credential_crypto import (
    CredentialDecryptionError,
    ENCRYPTED_VALUE_PREFIX,
    credential_fernet,
    decrypt_credential,
    decrypt_sensitive_mapping,
    encrypt_credential,
    encrypt_sensitive_mapping,
)
from app.core.encrypted_types import EncryptedCredential, EncryptedGatewayConfig


class CredentialCryptoTests(unittest.TestCase):
    def setUp(self) -> None:
        self.original_key = settings.CREDENTIAL_ENCRYPTION_KEY
        settings.CREDENTIAL_ENCRYPTION_KEY = Fernet.generate_key().decode("ascii")
        credential_fernet.cache_clear()

    def tearDown(self) -> None:
        settings.CREDENTIAL_ENCRYPTION_KEY = self.original_key
        credential_fernet.cache_clear()

    def test_credential_is_authenticated_and_not_stored_in_plaintext(self):
        plaintext = "production-payment-secret"

        encrypted = encrypt_credential(plaintext)

        self.assertTrue(encrypted.startswith(ENCRYPTED_VALUE_PREFIX))
        self.assertNotIn(plaintext, encrypted)
        self.assertEqual(decrypt_credential(encrypted), plaintext)

    def test_encryption_is_idempotent_for_already_encrypted_values(self):
        encrypted = encrypt_credential("secret")

        self.assertEqual(encrypt_credential(encrypted), encrypted)

    def test_legacy_plaintext_remains_readable_during_migration(self):
        self.assertEqual(decrypt_credential("legacy-secret"), "legacy-secret")

    def test_corrupted_ciphertext_is_rejected(self):
        with self.assertRaises(CredentialDecryptionError):
            decrypt_credential(f"{ENCRYPTED_VALUE_PREFIX}invalid-token")

    def test_sensitive_json_values_are_encrypted_but_checkout_config_is_preserved(self):
        config = {
            "events_secret": "webhook-secret",
            "callback_password": "callback-secret",
            "checkout_description": "Paga de forma segura con Wompi.",
            "checkout_accent": "emerald",
        }

        encrypted = encrypt_sensitive_mapping(config)

        self.assertNotEqual(encrypted["events_secret"], config["events_secret"])
        self.assertNotEqual(encrypted["callback_password"], config["callback_password"])
        self.assertEqual(encrypted["checkout_description"], config["checkout_description"])
        self.assertEqual(encrypted["checkout_accent"], config["checkout_accent"])
        self.assertEqual(decrypt_sensitive_mapping(encrypted), config)

    def test_sqlalchemy_types_enforce_the_same_storage_boundary(self):
        credential_type = EncryptedCredential()
        config_type = EncryptedGatewayConfig()

        stored_secret = credential_type.process_bind_param("secret", None)
        stored_config = config_type.process_bind_param(
            {"api_key": "private", "checkout_url": "https://checkout.example"},
            None,
        )

        self.assertNotEqual(stored_secret, "secret")
        self.assertNotEqual(stored_config["api_key"], "private")
        self.assertEqual(
            credential_type.process_result_value(stored_secret, None),
            "secret",
        )
        self.assertEqual(
            config_type.process_result_value(stored_config, None),
            {"api_key": "private", "checkout_url": "https://checkout.example"},
        )

    def test_nested_custom_headers_are_encrypted_recursively(self):
        config = {
            "headers": {
                "Authorization": "Bearer private-token",
                "X-API-Key": "private-api-key",
            },
            "metadata": {"label": "Proveedor principal"},
        }

        encrypted = encrypt_sensitive_mapping(config)

        self.assertNotEqual(encrypted["headers"]["Authorization"], config["headers"]["Authorization"])
        self.assertNotEqual(encrypted["headers"]["X-API-Key"], config["headers"]["X-API-Key"])
        self.assertEqual(encrypted["metadata"], config["metadata"])
        self.assertEqual(decrypt_sensitive_mapping(encrypted), config)


if __name__ == "__main__":
    unittest.main()

