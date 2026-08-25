from __future__ import annotations

from typing import Any, TypeVar

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


TenantRecord = TypeVar("TenantRecord")


async def get_company_owned(
    db: AsyncSession,
    model: Any,
    record_id: Any,
    company_id: Any,
    detail: str = "Registro no encontrado",
) -> TenantRecord:
    """Resolve one tenant-owned record or hide records from other companies."""
    result = await db.execute(
        select(model).where(
            model.id == record_id,
            model.company_id == company_id,
        )
    )
    record = result.scalar_one_or_none()
    if not record:
        raise HTTPException(status_code=404, detail=detail)
    return record
