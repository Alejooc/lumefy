"""SQLAlchemy types that keep gateway credentials encrypted at rest."""

from typing import Any

from sqlalchemy import JSON, String
from sqlalchemy.engine.interfaces import Dialect
from sqlalchemy.types import TypeDecorator

from app.core.credential_crypto import (
    decrypt_credential,
    decrypt_sensitive_mapping,
    encrypt_credential,
    encrypt_sensitive_mapping,
)


class EncryptedCredential(TypeDecorator[str]):
    impl = String
    cache_ok = True

    def process_bind_param(self, value: str | None, dialect: Dialect) -> str | None:
        return encrypt_credential(value)

    def process_result_value(self, value: str | None, dialect: Dialect) -> str | None:
        return decrypt_credential(value)


class EncryptedGatewayConfig(TypeDecorator[dict[str, Any]]):
    impl = JSON
    cache_ok = True

    def process_bind_param(self, value: dict[str, Any] | None, dialect: Dialect) -> dict[str, Any]:
        return encrypt_sensitive_mapping(value)

    def process_result_value(self, value: dict[str, Any] | None, dialect: Dialect) -> dict[str, Any]:
        return decrypt_sensitive_mapping(value)

