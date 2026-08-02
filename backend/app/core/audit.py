from sqlalchemy.ext.asyncio import AsyncSession
from app.models.audit import AuditLog
from fastapi.encoders import jsonable_encoder
from datetime import datetime, timezone
import logging

logger = logging.getLogger(__name__)

async def log_activity(
    db: AsyncSession,
    action: str,
    entity_type: str,
    entity_id: str,
    user_id: str = None,
    company_id: str = None,
    details: dict = None
):
    """
    Logs an activity to the audit_logs table.
    """
    try:
        audit_log = AuditLog(
            user_id=user_id,
            company_id=company_id,
            action=action,
            entity_type=entity_type,
            entity_id=str(entity_id) if entity_id else None,
            details=jsonable_encoder(details) if details else None,
            # Application time preserves event order when several events share
            # one database transaction (PostgreSQL transaction timestamps tie).
            created_at=datetime.now(timezone.utc),
        )
        db.add(audit_log)
        # We don't commit here usually to keep it in the same transaction as the action being logged.
        # However, if we want to log failures, we might want a separate session or commit.
        # For now, let's assume it's part of the main transaction flow involving `db`.
        # If the main transaction rolls back, the log rolls back too (which is usually desired for "Action X happened").
        # If we want to log "Attempt to do X failed", we need a different approach.
        
    except Exception as e:
        logger.error(f"Failed to create audit log: {e}")


async def log_sale_event(
    db: AsyncSession,
    sale_id: str,
    company_id: str,
    event_type: str,
    title: str,
    description: str | None = None,
    status: str = "info",
    provider: str | None = None,
    reference: str | None = None,
    metadata: dict | None = None,
    user_id: str | None = None,
) -> None:
    """Record a business event that can be shown in a sale timeline."""
    await log_activity(
        db,
        action=event_type,
        entity_type="Sale",
        entity_id=sale_id,
        user_id=user_id,
        company_id=company_id,
        details={
            "event_type": event_type,
            "title": title,
            "description": description,
            "status": status,
            "provider": provider,
            "reference": reference,
            "metadata": metadata or {},
            "actor_type": "user" if user_id else "system",
        },
    )
