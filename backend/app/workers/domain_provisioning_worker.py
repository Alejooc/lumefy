"""Provision verified storefront domains in Nginx Proxy Manager."""

from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import and_, func, or_, select

from app.core.config import settings
from app.core.database import SessionLocal
from app.models.storefront import StorefrontDomain
from app.services.npm_provisioning import NginxProxyManagerClient, NpmApiError


logger = logging.getLogger(__name__)
PROVISIONABLE_STATUSES = {"QUEUED", "RETRY", "NOT_CONFIGURED"}
REMOVAL_STATUSES = {"REMOVAL_QUEUED", "REMOVAL_RETRY"}
NPM_PROVISIONING_LOCK_ID = 0x4C554D45


def retry_delay_seconds(attempt: int, provider_retry_after: int | None = None) -> int:
    schedule = (300, 900, 3600)
    calculated = schedule[min(max(attempt - 1, 0), len(schedule) - 1)]
    return max(calculated, provider_retry_after or 0)


async def claim_pending_domains(limit: int) -> list[uuid.UUID]:
    now = datetime.now(timezone.utc)
    stale_before = now - timedelta(minutes=settings.NPM_PROVISIONING_STALE_MINUTES)
    async with SessionLocal() as db:
        result = await db.execute(
            select(StorefrontDomain)
            .where(
                or_(
                    and_(
                        StorefrontDomain.provisioning_status.in_(PROVISIONABLE_STATUSES | REMOVAL_STATUSES),
                        or_(
                            StorefrontDomain.provisioning_next_attempt_at.is_(None),
                            StorefrontDomain.provisioning_next_attempt_at <= now,
                        ),
                    ),
                    and_(
                        StorefrontDomain.provisioning_status.in_({"PROVISIONING", "REMOVING"}),
                        StorefrontDomain.provisioning_last_attempt_at <= stale_before,
                    ),
                )
            )
            .order_by(StorefrontDomain.provisioning_next_attempt_at.asc().nullsfirst(), StorefrontDomain.created_at.asc())
            .limit(limit)
            .with_for_update(skip_locked=True)
        )
        domains = result.scalars().all()
        claimed: list[uuid.UUID] = []
        for domain in domains:
            removing = not domain.is_active or domain.provisioning_status in REMOVAL_STATUSES | {"REMOVING"}
            domain.provisioning_status = "REMOVING" if removing else "PROVISIONING"
            domain.provisioning_attempts += 1
            domain.provisioning_last_attempt_at = now
            domain.provisioning_next_attempt_at = None
            claimed.append(domain.id)
        await db.commit()
        return claimed


async def process_claimed_domain(domain_id: uuid.UUID) -> None:
    async with SessionLocal() as db:
        domain = await db.get(StorefrontDomain, domain_id)
        if not domain or domain.provisioning_status not in {"PROVISIONING", "REMOVING"}:
            return
        removing = domain.provisioning_status == "REMOVING" or not domain.is_active
        domain_name = domain.domain
        proxy_host_id = domain.npm_proxy_host_id
        attempts = domain.provisioning_attempts

    try:
        client = NginxProxyManagerClient.from_settings()
        if removing:
            await asyncio.to_thread(client.deprovision_domain, domain_name, proxy_host_id)
            result = None
        else:
            result = await asyncio.to_thread(client.provision_domain, domain_name)
    except NpmApiError as exc:
        await record_failure(domain_id, exc, removing=removing, attempts=attempts)
        return
    except Exception as exc:  # Defensive boundary around a durable worker.
        logger.exception("Unexpected domain provisioning failure for %s", domain_name)
        await record_failure(
            domain_id,
            NpmApiError("Error inesperado al configurar el dominio.", retryable=True),
            removing=removing,
            attempts=attempts,
        )
        return

    async with SessionLocal() as db:
        domain = await db.get(StorefrontDomain, domain_id)
        if not domain:
            return
        # The merchant may register the same domain again while an old
        # removal is still running. Do not let that stale removal overwrite
        # the new PENDING_VERIFICATION/QUEUED state.
        if removing and domain.is_active:
            return
        domain.provisioning_error = None
        domain.provisioning_next_attempt_at = None
        if removing:
            domain.provisioning_status = "REMOVED"
            domain.npm_proxy_host_id = None
        elif not domain.is_active:
            # The merchant may delete the domain while NPM is issuing SSL.
            # Preserve the newly-created IDs and immediately queue cleanup.
            domain.npm_proxy_host_id = result.proxy_host_id
            domain.npm_certificate_id = result.certificate_id
            domain.provisioning_status = "REMOVAL_QUEUED"
            domain.provisioning_attempts = 0
            domain.provisioning_next_attempt_at = datetime.now(timezone.utc)
        else:
            domain.provisioning_status = "ACTIVE"
            domain.npm_proxy_host_id = result.proxy_host_id
            domain.npm_certificate_id = result.certificate_id
            domain.provisioned_at = datetime.now(timezone.utc)
        await db.commit()


async def record_failure(
    domain_id: uuid.UUID,
    error: NpmApiError,
    *,
    removing: bool,
    attempts: int,
) -> None:
    logger.warning("NPM provisioning failed for domain %s: %s", domain_id, error)
    async with SessionLocal() as db:
        domain = await db.get(StorefrontDomain, domain_id)
        if not domain:
            return
        # A retry from a stale removal must not change the state of a row that
        # has already been reactivated by the merchant.
        if removing and domain.is_active:
            return
        effective_removing = removing or not domain.is_active
        domain.provisioning_error = public_error_message(error)
        if error.retryable and attempts < settings.NPM_PROVISIONING_MAX_ATTEMPTS:
            delay = retry_delay_seconds(attempts, error.retry_after_seconds)
            domain.provisioning_status = "REMOVAL_RETRY" if effective_removing else "RETRY"
            domain.provisioning_next_attempt_at = datetime.now(timezone.utc) + timedelta(seconds=delay)
        else:
            domain.provisioning_status = "REMOVAL_FAILED" if effective_removing else "FAILED"
            domain.provisioning_next_attempt_at = None
        await db.commit()


def public_error_message(error: NpmApiError) -> str:
    message = str(error)
    if message.startswith("El dominio todavía no llega por HTTP"):
        return message
    if error.status_code == 409:
        return message
    if error.status_code in {401, 403}:
        return "La infraestructura de dominios requiere atención del administrador de la plataforma."
    if error.status_code == 429:
        return "El proveedor limitó temporalmente las solicitudes. Reintentaremos automáticamente."
    if error.status_code == 400:
        return "NPM no pudo validar o emitir el certificado. Revisa que el dominio apunte al servidor de Lumefy."
    if error.retryable:
        return "El servicio de dominios no respondió. Reintentaremos automáticamente."
    return "No se pudo configurar el dominio. Contacta al administrador de la plataforma."


async def process_pending_domains_once() -> int:
    # Certbot inside NPM is single-process. A PostgreSQL advisory lock keeps
    # multiple accidental worker replicas from issuing certificates in parallel.
    async with SessionLocal() as lock_db:
        acquired = await lock_db.scalar(select(func.pg_try_advisory_lock(NPM_PROVISIONING_LOCK_ID)))
        if not acquired:
            return 0
        try:
            claimed = await claim_pending_domains(settings.NPM_PROVISIONING_CONCURRENCY)
            if claimed:
                await asyncio.gather(*(process_claimed_domain(domain_id) for domain_id in claimed))
            return len(claimed)
        finally:
            await lock_db.scalar(select(func.pg_advisory_unlock(NPM_PROVISIONING_LOCK_ID)))


async def main() -> None:
    logging.basicConfig(level=logging.INFO)
    if not settings.NPM_PROVISIONING_ENABLED:
        logger.warning("NPM domain provisioning is disabled; the worker will remain idle.")
    while True:
        if settings.NPM_PROVISIONING_ENABLED:
            try:
                await process_pending_domains_once()
            except Exception:
                logger.exception("Domain provisioning polling cycle failed")
        await asyncio.sleep(settings.NPM_PROVISIONING_POLL_SECONDS)


if __name__ == "__main__":
    asyncio.run(main())
