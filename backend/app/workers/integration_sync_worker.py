"""Durable catalog and inventory synchronization worker."""

from __future__ import annotations

import asyncio
import logging
import os
from datetime import datetime, timedelta
from uuid import UUID

from sqlalchemy import exists, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import aliased

from app.core.database import SessionLocal
from app.models.integration import IntegrationSource, IntegrationSyncRun
from app.services.integration_service import IntegrationSyncConflict, enqueue_sync, execute_sync_run


LOGGER = logging.getLogger("lumefy.integration_sync_worker")
POLL_SECONDS = max(1.0, float(os.getenv("INTEGRATION_SYNC_POLL_SECONDS", "2")))
STALE_MINUTES = max(10, int(os.getenv("INTEGRATION_SYNC_STALE_MINUTES", "60")))


async def enqueue_due_inventory() -> int:
    now = datetime.utcnow()
    async with SessionLocal() as db:
        due_source_ids = list((await db.execute(
            select(IntegrationSource.id)
            .where(
                IntegrationSource.is_active.is_(True),
                IntegrationSource.inventory_sync_mode == "AUTOMATIC",
                IntegrationSource.inventory_sync_interval_minutes.is_not(None),
                IntegrationSource.next_inventory_sync_at.is_not(None),
                IntegrationSource.next_inventory_sync_at <= now,
            )
            .order_by(IntegrationSource.next_inventory_sync_at.asc())
            .limit(25)
        )).scalars().all())

    enqueued = 0
    for source_id in due_source_ids:
        async with SessionLocal() as db:
            source = await db.get(IntegrationSource, source_id)
            if not source or not source.is_active or source.inventory_sync_mode != "AUTOMATIC":
                continue
            interval = source.inventory_sync_interval_minutes
            if not interval:
                continue
            try:
                await enqueue_sync(
                    db,
                    source,
                    None,
                    sync_type="INVENTORY",
                    trigger_type="SCHEDULED",
                )
                enqueued += 1
            except IntegrationSyncConflict:
                # An inventory run is already queued/running. Advancing the due
                # time avoids hot-looping while preserving the configured cadence.
                pass
            source = await db.get(IntegrationSource, source_id)
            if source:
                source.next_inventory_sync_at = now + timedelta(minutes=interval)
                await db.commit()
    return enqueued


async def recover_stale_runs() -> int:
    threshold = datetime.utcnow() - timedelta(minutes=STALE_MINUTES)
    async with SessionLocal() as db:
        runs = list((await db.execute(
            select(IntegrationSyncRun)
            .where(
                IntegrationSyncRun.status == "RUNNING",
                IntegrationSyncRun.started_at.is_not(None),
                IntegrationSyncRun.started_at < threshold,
            )
            .with_for_update(skip_locked=True)
        )).scalars().all())
        for run in runs:
            run.status = "FAILED"
            run.finished_at = datetime.utcnow()
            run.error_message = "La ejecución fue recuperada después de quedar interrumpida."
            source = await db.get(IntegrationSource, run.source_id)
            if source:
                source.status = "ERROR"
                source.last_sync_status = "FAILED"
                source.last_error = run.error_message
        await db.commit()
        return len(runs)


async def claim_next_run() -> UUID | None:
    running = aliased(IntegrationSyncRun)
    async with SessionLocal() as db:
        run = (await db.execute(
            select(IntegrationSyncRun)
            .where(
                IntegrationSyncRun.status == "QUEUED",
                ~exists().where(
                    running.source_id == IntegrationSyncRun.source_id,
                    running.status == "RUNNING",
                ),
            )
            .order_by(IntegrationSyncRun.queued_at.asc(), IntegrationSyncRun.created_at.asc())
            .limit(1)
            .with_for_update(skip_locked=True)
        )).scalars().first()
        if not run:
            return None
        run.status = "RUNNING"
        run.started_at = datetime.utcnow()
        try:
            await db.commit()
        except IntegrityError:
            # Another worker won the per-source running constraint.
            await db.rollback()
            return None
        return run.id


async def process_run(run_id: UUID) -> None:
    async with SessionLocal() as db:
        run = await db.get(IntegrationSyncRun, run_id)
        if not run or run.status != "RUNNING":
            return
        await execute_sync_run(db, run)


async def main() -> None:
    logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
    while True:
        try:
            await recover_stale_runs()
            await enqueue_due_inventory()
            run_id = await claim_next_run()
            if run_id:
                await process_run(run_id)
                continue
        except Exception:  # noqa: BLE001 - keep the durable worker alive and observable
            LOGGER.exception("Integration sync worker iteration failed")
        await asyncio.sleep(POLL_SECONDS)


if __name__ == "__main__":
    asyncio.run(main())
