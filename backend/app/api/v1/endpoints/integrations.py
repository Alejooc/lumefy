from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.permissions import PermissionChecker
from app.models.integration import IntegrationSource, IntegrationSyncRun
from app.models.user import User
from app.schemas import integration as schemas
from app.services.integration_service import (
    IntegrationRequestError,
    preview_source,
    suggest_mapping_source,
    sync_source,
    test_source,
    validate_source,
)


router = APIRouter()


def _serialize_source(source: IntegrationSource) -> dict[str, Any]:
    return {
        "id": source.id,
        "company_id": source.company_id,
        "name": source.name,
        "provider_key": source.provider_key,
        "source_type": source.source_type,
        "base_url": source.base_url,
        "auth_type": source.auth_type,
        "credentials_configured": bool(source.credentials),
        "configuration": source.configuration or {},
        "status": source.status,
        "is_active": source.is_active,
        "last_tested_at": source.last_tested_at,
        "last_synced_at": source.last_synced_at,
        "last_sync_status": source.last_sync_status,
        "last_error": source.last_error,
        "created_at": source.created_at,
        "updated_at": source.updated_at,
    }


def _source_query(company_id: UUID):
    return select(IntegrationSource).where(IntegrationSource.company_id == company_id)


async def _get_source(db: AsyncSession, source_id: UUID, company_id: UUID) -> IntegrationSource:
    source = (await db.execute(
        _source_query(company_id).where(IntegrationSource.id == source_id)
    )).scalars().first()
    if not source:
        raise HTTPException(status_code=404, detail="Origen de datos no encontrado")
    return source


@router.get("/sources", response_model=list[schemas.IntegrationSourceOut])
async def list_sources(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(PermissionChecker("manage_company")),
) -> list[dict[str, Any]]:
    result = await db.execute(_source_query(current_user.company_id).order_by(IntegrationSource.created_at.desc()))
    return [_serialize_source(source) for source in result.scalars().all()]


@router.post("/sources", response_model=schemas.IntegrationSourceOut, status_code=201)
async def create_source(
    payload: schemas.IntegrationSourceCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(PermissionChecker("manage_company")),
) -> dict[str, Any]:
    source = IntegrationSource(
        name=payload.name.strip(),
        provider_key=payload.provider_key,
        source_type=payload.source_type.upper(),
        base_url=payload.base_url.strip(),
        auth_type=payload.auth_type,
        credentials=payload.credentials,
        configuration=payload.configuration,
        status="DRAFT",
        company_id=current_user.company_id,
        created_by_id=current_user.id,
        updated_by_id=current_user.id,
    )
    try:
        validate_source(source)
    except IntegrationRequestError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    db.add(source)
    await db.commit()
    await db.refresh(source)
    return _serialize_source(source)


@router.get("/sources/{source_id}", response_model=schemas.IntegrationSourceOut)
async def get_source(
    source_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(PermissionChecker("manage_company")),
) -> dict[str, Any]:
    return _serialize_source(await _get_source(db, source_id, current_user.company_id))


@router.put("/sources/{source_id}", response_model=schemas.IntegrationSourceOut)
async def update_source(
    source_id: UUID,
    payload: schemas.IntegrationSourceUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(PermissionChecker("manage_company")),
) -> dict[str, Any]:
    source = await _get_source(db, source_id, current_user.company_id)
    changes = payload.model_dump(exclude_unset=True)
    credentials = changes.pop("credentials", None)
    if credentials is not None:
        source.credentials = {**(source.credentials or {}), **credentials}
    if str(changes.get("auth_type") or source.auth_type).lower() == "none":
        source.credentials = {}
    for field, value in changes.items():
        if field == "source_type" and value:
            value = value.upper()
        setattr(source, field, value)
    source.updated_by_id = current_user.id
    source.status = "DRAFT" if source.is_active else "DISABLED"
    source.last_error = None
    try:
        validate_source(source)
    except IntegrationRequestError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    await db.commit()
    await db.refresh(source)
    return _serialize_source(source)


@router.delete("/sources/{source_id}")
async def disable_source(
    source_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(PermissionChecker("manage_company")),
) -> dict[str, bool]:
    source = await _get_source(db, source_id, current_user.company_id)
    source.is_active = False
    source.status = "DISABLED"
    source.updated_by_id = current_user.id
    await db.commit()
    return {"ok": True}


@router.post("/sources/{source_id}/test", response_model=schemas.IntegrationTestOut)
async def test_connection(
    source_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(PermissionChecker("manage_company")),
) -> dict[str, Any]:
    source = await _get_source(db, source_id, current_user.company_id)
    try:
        result = await test_source(source)
        source.status = "CONNECTED"
        source.last_tested_at = datetime.utcnow()
        source.last_error = None
        await db.commit()
        return result
    except IntegrationRequestError as exc:
        source.status = "ERROR"
        source.last_tested_at = datetime.utcnow()
        source.last_error = str(exc)[:2000]
        await db.commit()
        return {"success": False, "status_code": exc.status_code, "message": str(exc), "sample_count": 0}


@router.post("/sources/{source_id}/preview", response_model=schemas.IntegrationPreviewOut)
async def preview_connection(
    source_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(PermissionChecker("manage_company")),
) -> dict[str, Any]:
    source = await _get_source(db, source_id, current_user.company_id)
    try:
        return await preview_source(source)
    except IntegrationRequestError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("/sources/{source_id}/mapping-suggestion", response_model=schemas.IntegrationMappingOut)
async def mapping_suggestion(
    source_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(PermissionChecker("manage_company")),
) -> dict[str, Any]:
    source = await _get_source(db, source_id, current_user.company_id)
    try:
        return await suggest_mapping_source(source)
    except IntegrationRequestError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("/sources/{source_id}/mapping-confirm", response_model=schemas.IntegrationSourceOut)
async def confirm_mapping(
    source_id: UUID,
    payload: schemas.IntegrationMappingConfirm,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(PermissionChecker("manage_company")),
) -> dict[str, Any]:
    source = await _get_source(db, source_id, current_user.company_id)
    required_fields = ["product.external_id", "product.name"]
    missing_fields = [field for field in required_fields if not str(payload.mapping.get(field) or "").strip()]
    if missing_fields:
        raise HTTPException(
            status_code=422,
            detail=f"Confirma al menos estos campos requeridos: {', '.join(missing_fields)}",
        )
    configuration = {
        **(source.configuration or {}),
        "catalog_mode": payload.catalog_mode or "auto",
        "mapping_status": "confirmed",
        "field_map": payload.mapping,
        "collections": payload.collections,
    }
    source.configuration = configuration
    source.status = "DRAFT" if source.is_active else "DISABLED"
    source.last_error = None
    source.updated_by_id = current_user.id
    await db.commit()
    await db.refresh(source)
    return _serialize_source(source)


@router.post("/sources/{source_id}/sync", response_model=schemas.IntegrationSyncRunOut)
async def run_sync(
    source_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(PermissionChecker("manage_company")),
) -> IntegrationSyncRun:
    source = await _get_source(db, source_id, current_user.company_id)
    if not source.is_active:
        raise HTTPException(status_code=400, detail="El origen de datos está desactivado")
    run = await sync_source(db, source, current_user.id)
    if run.status == "FAILED":
        raise HTTPException(status_code=502, detail=run.error_message or "La sincronización falló")
    return run


@router.get("/sources/{source_id}/runs", response_model=list[schemas.IntegrationSyncRunOut])
async def list_runs(
    source_id: UUID,
    limit: int = 20,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(PermissionChecker("manage_company")),
) -> list[IntegrationSyncRun]:
    await _get_source(db, source_id, current_user.company_id)
    result = await db.execute(
        select(IntegrationSyncRun)
        .where(
            IntegrationSyncRun.source_id == source_id,
            IntegrationSyncRun.company_id == current_user.company_id,
        )
        .order_by(IntegrationSyncRun.created_at.desc())
        .limit(max(1, min(limit, 100)))
    )
    return list(result.scalars().all())
