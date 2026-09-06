from datetime import datetime, timedelta, timezone

from app.services.storefront_payment_expiry import payment_pending_deadline, payment_pending_ttl


def test_online_provider_has_short_pending_window():
    assert payment_pending_ttl("PAYU") == timedelta(hours=2)


def test_manual_transfer_has_longer_window():
    assert payment_pending_ttl("manual_transfer") == timedelta(hours=48)


def test_deadline_normalizes_naive_creation_time_to_utc():
    created_at = datetime(2026, 9, 5, 12, 0, 0)
    assert payment_pending_deadline("addi", created_at=created_at) == datetime(2026, 9, 6, 12, 0, 0, tzinfo=timezone.utc)
