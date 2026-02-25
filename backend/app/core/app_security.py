import hashlib
import hmac
import secrets


def generate_api_key() -> str:
    return f"lumefy_app_{secrets.token_urlsafe(32)}"


def api_key_prefix(api_key: str) -> str:
    return api_key[:16]


def hash_api_key(api_key: str) -> str:
    return hashlib.sha256(api_key.encode("utf-8")).hexdigest()


def verify_api_key(raw_api_key: str, stored_hash: str | None) -> bool:
    if not stored_hash:
        return False
    return hmac.compare_digest(hash_api_key(raw_api_key), stored_hash)


def generate_webhook_secret() -> str:
    return secrets.token_urlsafe(48)


def sign_webhook_payload(secret: str, payload: bytes) -> str:
    return hmac.new(secret.encode("utf-8"), payload, hashlib.sha256).hexdigest()


def generate_client_id() -> str:
    return f"lumefy_cli_{secrets.token_urlsafe(18)}"


def generate_client_secret() -> str:
    return f"lumefy_sec_{secrets.token_urlsafe(36)}"
