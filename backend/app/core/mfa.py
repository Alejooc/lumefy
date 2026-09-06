"""Small, dependency-free TOTP helpers used for protecting platform accounts."""

from __future__ import annotations

import base64
import binascii
import hashlib
import hmac
import secrets
import time
from datetime import datetime, timezone
from urllib.parse import quote


TOTP_PERIOD_SECONDS = 30
TOTP_DIGITS = 6
TOTP_SECRET_BYTES = 20


def generate_totp_secret() -> str:
    """Generate a Google Authenticator-compatible base32 secret."""

    return base64.b32encode(secrets.token_bytes(TOTP_SECRET_BYTES)).decode("ascii").rstrip("=")


def build_totp_uri(secret: str, *, account: str, issuer: str = "Lumefy") -> str:
    """Build the otpauth URI without exposing it in logs or server-side audit data."""

    label = f"{issuer}:{account}"
    return (
        "otpauth://totp/"
        f"{quote(label, safe='')}?secret={quote(secret)}"
        f"&issuer={quote(issuer)}&algorithm=SHA1&digits={TOTP_DIGITS}&period={TOTP_PERIOD_SECONDS}"
    )


def _secret_bytes(secret: str) -> bytes:
    normalized = "".join(str(secret or "").split()).upper()
    padding = "=" * (-len(normalized) % 8)
    return base64.b32decode(normalized + padding, casefold=True)


def _totp_at_step(secret: str, step: int) -> str:
    digest = hmac.new(
        _secret_bytes(secret),
        step.to_bytes(8, byteorder="big", signed=False),
        hashlib.sha1,
    ).digest()
    offset = digest[-1] & 0x0F
    binary = int.from_bytes(digest[offset : offset + 4], byteorder="big") & 0x7FFFFFFF
    return str(binary % (10**TOTP_DIGITS)).zfill(TOTP_DIGITS)


def verify_totp(secret: str, code: str, *, at: datetime | None = None, window: int = 1) -> int | None:
    """Return the accepted time-step, or ``None`` for an invalid code."""

    normalized_code = "".join(str(code or "").split())
    if len(normalized_code) != TOTP_DIGITS or not normalized_code.isdigit():
        return None

    moment = at or datetime.now(timezone.utc)
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)
    current_step = int(moment.timestamp()) // TOTP_PERIOD_SECONDS
    try:
        for offset in range(-window, window + 1):
            step = current_step + offset
            if step >= 0 and hmac.compare_digest(_totp_at_step(secret, step), normalized_code):
                return step
    except (ValueError, binascii.Error):
        return None
    return None


def generate_recovery_codes(count: int = 10) -> list[str]:
    """Generate printable one-time recovery codes."""

    codes: list[str] = []
    for _ in range(count):
        value = secrets.token_hex(4).upper()
        codes.append(f"{value[:4]}-{value[4:]}")
    return codes


def normalize_recovery_code(code: str) -> str:
    return "".join(str(code or "").upper().split()).replace("-", "")


def consume_recovery_code(codes: list[str], supplied_code: str) -> tuple[list[str], bool]:
    """Remove a matching recovery code using constant-time comparisons."""

    candidate = normalize_recovery_code(supplied_code)
    remaining: list[str] = []
    matched = False
    for code in codes:
        if not matched and hmac.compare_digest(normalize_recovery_code(code), candidate):
            matched = True
            continue
        remaining.append(code)
    return remaining, matched


def hash_challenge_id(challenge_id: str) -> str:
    return hashlib.sha256(challenge_id.encode("utf-8")).hexdigest()
