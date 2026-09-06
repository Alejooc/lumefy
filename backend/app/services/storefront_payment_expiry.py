"""Shared payment-pending expiry policy for storefront orders."""

from datetime import datetime, timedelta, timezone


# Pending payment is not the same as an abandoned order for every method.
# Cash-on-delivery remains valid through fulfillment, while online providers
# get a bounded reservation window. These defaults are intentionally explicit
# until each provider's settlement SLA is configured per storefront.
PAYMENT_PENDING_TTL = {
    "wompi": timedelta(hours=2),
    "payu": timedelta(hours=2),
    "mercadopago": timedelta(hours=2),
    "addi": timedelta(hours=24),
    "sistecredito": timedelta(hours=24),
    "manual_transfer": timedelta(hours=48),
    "whatsapp": timedelta(hours=48),
    "cod": timedelta(days=30),
}
DEFAULT_PAYMENT_PENDING_TTL = timedelta(hours=2)


def payment_pending_ttl(provider: str | None) -> timedelta:
    return PAYMENT_PENDING_TTL.get((provider or "").strip().lower(), DEFAULT_PAYMENT_PENDING_TTL)


def payment_pending_deadline(
    provider: str | None,
    *,
    created_at: datetime | None = None,
) -> datetime:
    base = created_at or datetime.now(timezone.utc)
    if base.tzinfo is None:
        base = base.replace(tzinfo=timezone.utc)
    else:
        base = base.astimezone(timezone.utc)
    return base + payment_pending_ttl(provider)
