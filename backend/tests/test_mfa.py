from datetime import datetime, timezone

from app.core.mfa import (
    TOTP_PERIOD_SECONDS,
    build_totp_uri,
    consume_recovery_code,
    generate_recovery_codes,
    verify_totp,
)


def _code(secret: str, step: int) -> str:
    from app.core.mfa import _totp_at_step

    return _totp_at_step(secret, step)


def test_totp_accepts_current_step_and_rejects_replay_window_outside_range():
    secret = "JBSWY3DPEHPK3PXP"
    step = 1_700_000_000 // TOTP_PERIOD_SECONDS
    current = datetime.fromtimestamp(step * TOTP_PERIOD_SECONDS, tz=timezone.utc)

    assert verify_totp(secret, _code(secret, step), at=current, window=1) == step
    assert verify_totp(secret, _code(secret, step - 2), at=current, window=1) is None


def test_recovery_codes_are_one_time_and_uri_is_authenticator_compatible():
    codes = generate_recovery_codes(2)
    remaining, matched = consume_recovery_code(codes, codes[0].lower())

    assert matched is True
    assert remaining == [codes[1]]
    remaining_after_replay, replayed = consume_recovery_code(remaining, codes[0])
    assert replayed is False
    assert remaining_after_replay == remaining
    assert build_totp_uri("ABC123", account="owner@example.com").startswith("otpauth://totp/")

