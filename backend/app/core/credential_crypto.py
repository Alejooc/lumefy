"""Application-level encryption for credentials persisted by Lumefy."""

from __future__ import annotations

import base64
import hashlib
from functools import lru_cache
from typing import Any, Mapping

from cryptography.fernet import Fernet, InvalidToken


ENCRYPTED_VALUE_PREFIX = "enc:v1:"
SENSITIVE_GATEWAY_CONFIG_KEYS = frozenset(
    {
        "access_token",
        "api_key",
        "api_login",
        "callback_password",
        "client_secret",
        "events_secret",
        "integrity_secret",
        "password",
        "private_key",
        "secret",
        "signing_secret",
        "token",
        "webhook_secret",
    }
)


class CredentialDecryptionError(ValueError):
    """Raised when an encrypted credential cannot be authenticated."""


def _development_fallback_key(secret_key: str) -> bytes:
    digest = hashlib.sha256(secret_key.encode("utf-8")).digest()
    return base64.urlsafe_b64encode(digest)


@lru_cache(maxsize=1)
def credential_fernet() -> Fernet:
    # Import lazily to avoid a circular dependency while Settings is created.
    from app.core.config import settings

    configured_key = settings.CREDENTIAL_ENCRYPTION_KEY
    if configured_key:
        return Fernet(configured_key.encode("ascii"))
    if settings.ENVIRONMENT.lower() == "production":
        raise RuntimeError("CREDENTIAL_ENCRYPTION_KEY is required in production")
    return Fernet(_development_fallback_key(settings.SECRET_KEY))


def is_encrypted_value(value: Any) -> bool:
    return isinstance(value, str) and value.startswith(ENCRYPTED_VALUE_PREFIX)


def encrypt_credential(value: str | None) -> str | None:
    if value is None or value == "" or is_encrypted_value(value):
        return value
    token = credential_fernet().encrypt(value.encode("utf-8")).decode("ascii")
    return f"{ENCRYPTED_VALUE_PREFIX}{token}"


def decrypt_credential(value: str | None) -> str | None:
    if value is None or value == "" or not is_encrypted_value(value):
        # Plaintext is accepted only for backward-compatible migration reads.
        return value
    token = value.removeprefix(ENCRYPTED_VALUE_PREFIX)
    try:
        return credential_fernet().decrypt(token.encode("ascii")).decode("utf-8")
    except (InvalidToken, UnicodeDecodeError, ValueError) as exc:
        raise CredentialDecryptionError("Stored credential could not be decrypted") from exc


def encrypt_sensitive_mapping(config: Mapping[str, Any] | None) -> dict[str, Any]:
    encrypted = dict(config or {})
    for key, value in encrypted.items():
        if key.lower() in SENSITIVE_GATEWAY_CONFIG_KEYS and value not in (None, ""):
            encrypted[key] = encrypt_credential(str(value))
    return encrypted


def decrypt_sensitive_mapping(config: Mapping[str, Any] | None) -> dict[str, Any]:
    decrypted = dict(config or {})
    for key, value in decrypted.items():
        if key.lower() in SENSITIVE_GATEWAY_CONFIG_KEYS and isinstance(value, str):
            decrypted[key] = decrypt_credential(value)
    return decrypted

