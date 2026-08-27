from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from sqlalchemy.exc import IntegrityError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.permissions import PermissionChecker
from app.models.integration import IntegrationOrderLink, IntegrationSource, IntegrationSyncRun, IntegrationWebhookEvent
from app.models.app_definition import AppDefinition
from app.models.company_app_install import CompanyAppInstall
from app.models.user import User
from app.schemas import integration as schemas
from app.services.integration_service import (
    IntegrationRequestError,
    IntegrationSyncConflict,
    enqueue_sync,
    preflight_source,
    preview_source,
    request_asset,
    suggest_mapping_source,
    test_source,
    validate_source,
    verify_webhook_event,
)
from app.services.integration_orders import export_sale_to_source
from app.models.sale import Sale, SaleItem
from sqlalchemy.orm import selectinload


router = APIRouter()

ELEGANTHOME_PROVIDER_KEY = "eleganthome"


async def _active_app_install(
    db: AsyncSession,
    company_id: UUID,
    slug: str,
) -> CompanyAppInstall | None:
    result = await db.execute(
        select(CompanyAppInstall)
        .join(AppDefinition, AppDefinition.id == CompanyAppInstall.app_id)
        .where(
            CompanyAppInstall.company_id == company_id,
            CompanyAppInstall.is_enabled.is_(True),
            AppDefinition.slug == slug,
            AppDefinition.is_active.is_(True),
        )
    )
    return result.scalars().first()


async def _require_provider_install(
    db: AsyncSession,
    company_id: UUID,
    provider_key: str,
) -> CompanyAppInstall | None:
    if provider_key != ELEGANTHOME_PROVIDER_KEY:
        return None
    install = await _active_app_install(db, company_id, ELEGANTHOME_PROVIDER_KEY)
    if not install:
        raise HTTPException(
            status_code=403,
            detail="Instala y activa la app ElegantHome antes de crear esta conexión.",
        )
    return install


async def _validate_source_install(
    db: AsyncSession,
    source: IntegrationSource,
    company_id: UUID,
) -> None:
    if not source.app_install_id:
        return
    install = await db.scalar(
        select(CompanyAppInstall).where(
            CompanyAppInstall.id == source.app_install_id,
            CompanyAppInstall.company_id == company_id,
            CompanyAppInstall.is_enabled.is_(True),
        )
    )
    if not install:
        raise HTTPException(status_code=403, detail="La app asociada a esta conexión no está activa.")


@router.get("/assets")
async def proxy_asset(
    url: str = Query(..., min_length=1, max_length=2000),
    source_id: UUID | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
) -> Response:
    """Serve provider images with the source's server-side credentials.

    Catalog payloads can contain images under an authenticated REST endpoint.
    Browsers and Next's image optimizer cannot send the provider API key, so
    the storefront uses this narrowly scoped proxy instead.
    """
    from app.services.integration_service import _asset_url_matches_source

    # A paused/failed source may still own products already published in the
    # storefront. Serving those existing assets must not require reactivating
    # catalog or inventory synchronization.
    sources = (await db.execute(select(IntegrationSource))).scalars().all()
    matching_sources = [candidate for candidate in sources if _asset_url_matches_source(candidate, url)]
    if source_id:
        # A public source_id is only a disambiguation hint. Never load a
        # source by id before proving that the requested URL belongs to it.
        matching_sources = [candidate for candidate in matching_sources if candidate.id == source_id]
    if len(matching_sources) > 1:
        # Never select the first company's credentials for an ambiguous
        # provider URL. Local cached images do not need this proxy.
        raise HTTPException(
            status_code=409,
            detail="La imagen coincide con más de un origen; vuelve a sincronizar el catálogo.",
        )
    source = matching_sources[0] if matching_sources else None
    if source is None:
        raise HTTPException(status_code=404, detail="Imagen no asociada a un origen activo")
    auth_type = (source.auth_type or "none").strip().lower()
    if auth_type not in {"none", ""} or bool(source.credentials):
        raise HTTPException(
            status_code=403,
            detail="Los activos de fuentes autenticadas deben servirse desde una copia local publicada.",
        )
    try:
        content_type, body = await request_asset(source, url)
    except IntegrationRequestError as exc:
        status_code = exc.status_code if exc.status_code and 400 <= exc.status_code < 500 else 502
        raise HTTPException(status_code=status_code, detail="No se pudo cargar la imagen del proveedor") from exc
    return Response(
        content=body,
        media_type=content_type,
        headers={"Cache-Control": "public, max-age=86400, stale-while-revalidate=604800"},
    )


def _serialize_source(source: IntegrationSource) -> dict[str, Any]:
    return {
        "id": source.id,
        "company_id": source.company_id,
        "app_install_id": source.app_install_id,
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
        "last_catalog_synced_at": source.last_catalog_synced_at,
        "last_inventory_synced_at": source.last_inventory_synced_at,
        "last_sync_status": source.last_sync_status,
        "last_error": source.last_error,
        "inventory_sync_mode": source.inventory_sync_mode,
        "inventory_sync_interval_minutes": source.inventory_sync_interval_minutes,
        "next_inventory_sync_at": source.next_inventory_sync_at,
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
    await _validate_source_install(db, source, company_id)
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
    provider_key = (payload.provider_key or "custom_rest").strip().lower()
    app_install = await _require_provider_install(db, current_user.company_id, provider_key)
    source = IntegrationSource(
        name=payload.name.strip(),
        provider_key=provider_key,
        app_install_id=app_install.id if app_install else None,
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
    target_provider_key = str(changes.get("provider_key") or source.provider_key or "custom_rest").strip().lower()
    app_install = await _require_provider_install(db, current_user.company_id, target_provider_key)
    if "provider_key" in changes:
        changes["provider_key"] = target_provider_key
    if target_provider_key == ELEGANTHOME_PROVIDER_KEY:
        source.app_install_id = app_install.id if app_install else source.app_install_id
    elif "provider_key" in changes:
        source.app_install_id = None
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
    if (
        source.is_active
        and source.inventory_sync_mode == "AUTOMATIC"
        and source.inventory_sync_interval_minutes
        and source.next_inventory_sync_at is None
    ):
        source.next_inventory_sync_at = datetime.utcnow() + timedelta(
            minutes=source.inventory_sync_interval_minutes
        )
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
    source.next_inventory_sync_at = None
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


@router.post("/sources/{source_id}/preflight", response_model=schemas.IntegrationPreflightOut)
async def preflight_connection(
    source_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(PermissionChecker("manage_company")),
) -> dict[str, Any]:
    """Validate an origin without creating a run or modifying business data."""
    source = await _get_source(db, source_id, current_user.company_id)
    return await preflight_source(db, source)


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


async def _enqueue_manual_sync(
    db: AsyncSession,
    source: IntegrationSource,
    current_user: User,
    sync_type: str,
) -> IntegrationSyncRun:
    if not source.is_active:
        raise HTTPException(status_code=400, detail="El origen de datos está desactivado")
    try:
        return await enqueue_sync(
            db,
            source,
            current_user.id,
            sync_type=sync_type,
            trigger_type="MANUAL",
        )
    except IntegrationSyncConflict as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.put("/sources/{source_id}/inventory-schedule", response_model=schemas.IntegrationSourceOut)
async def update_inventory_schedule(
    source_id: UUID,
    payload: schemas.IntegrationInventoryScheduleUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(PermissionChecker("manage_company")),
) -> dict[str, Any]:
    source = await _get_source(db, source_id, current_user.company_id)
    if payload.mode == "AUTOMATIC" and not source.is_active:
        raise HTTPException(status_code=400, detail="Activa el origen antes de programar el inventario")
    source.inventory_sync_mode = payload.mode
    source.inventory_sync_interval_minutes = payload.interval_minutes
    source.next_inventory_sync_at = (
        datetime.utcnow() + timedelta(minutes=payload.interval_minutes)
        if payload.mode == "AUTOMATIC" and payload.interval_minutes
        else None
    )
    source.updated_by_id = current_user.id
    await db.commit()
    await db.refresh(source)
    return _serialize_source(source)


@router.post(
    "/sources/{source_id}/sync/catalog",
    response_model=schemas.IntegrationSyncRunOut,
    status_code=202,
)
async def run_catalog_sync(
    source_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(PermissionChecker("manage_company")),
) -> IntegrationSyncRun:
    source = await _get_source(db, source_id, current_user.company_id)
    return await _enqueue_manual_sync(db, source, current_user, "CATALOG")


@router.post(
    "/sources/{source_id}/sync/inventory",
    response_model=schemas.IntegrationSyncRunOut,
    status_code=202,
)
async def run_inventory_sync(
    source_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(PermissionChecker("manage_company")),
) -> IntegrationSyncRun:
    source = await _get_source(db, source_id, current_user.company_id)
    return await _enqueue_manual_sync(db, source, current_user, "INVENTORY")


@router.post(
    "/sources/{source_id}/sync/orders",
    response_model=schemas.IntegrationSyncRunOut,
    status_code=202,
)
async def run_orders_sync(
    source_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(PermissionChecker("manage_company")),
) -> IntegrationSyncRun:
    source = await _get_source(db, source_id, current_user.company_id)
    return await _enqueue_manual_sync(db, source, current_user, "ORDERS")


@router.get("/sources/{source_id}/orders", response_model=list[schemas.IntegrationOrderLinkOut])
async def list_external_orders(
    source_id: UUID,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(PermissionChecker("manage_company")),
) -> list[Any]:
    await _get_source(db, source_id, current_user.company_id)
    result = await db.execute(
        select(IntegrationOrderLink)
        .where(
            IntegrationOrderLink.source_id == source_id,
            IntegrationOrderLink.company_id == current_user.company_id,
        )
        .order_by(IntegrationOrderLink.created_at.desc())
        .limit(max(1, min(limit, 200)))
    )
    return list(result.scalars().all())


@router.post("/sources/{source_id}/orders/export/{sale_id}", response_model=schemas.IntegrationOrderLinkOut)
async def export_external_order(
    source_id: UUID,
    sale_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(PermissionChecker("manage_company")),
) -> Any:
    source = await _get_source(db, source_id, current_user.company_id)
    result = await db.execute(
        select(Sale)
        .options(
            selectinload(Sale.items).selectinload(SaleItem.product),
            selectinload(Sale.items).selectinload(SaleItem.variant),
            selectinload(Sale.client),
        )
        .where(Sale.id == sale_id, Sale.company_id == current_user.company_id)
    )
    sale = result.scalars().first()
    if not sale:
        raise HTTPException(status_code=404, detail="Venta no encontrada")
    try:
        link = await export_sale_to_source(db, source, sale)
        await db.commit()
        await db.refresh(link)
        return link
    except IntegrationRequestError as exc:
        await db.rollback()
        raise HTTPException(status_code=exc.status_code or 422, detail=str(exc)) from exc


@router.post(
    "/sources/{source_id}/sync",
    response_model=schemas.IntegrationSyncRunOut,
    status_code=202,
    deprecated=True,
)
async def run_sync(
    source_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(PermissionChecker("manage_company")),
) -> IntegrationSyncRun:
    """Compatibility endpoint. New clients should queue catalog and inventory separately."""
    source = await _get_source(db, source_id, current_user.company_id)
    return await _enqueue_manual_sync(db, source, current_user, "FULL")


@router.post(
    "/sources/{source_id}/webhook",
    response_model=schemas.IntegrationWebhookOut,
    status_code=202,
)
async def receive_source_webhook(
    source_id: UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Accept one signed provider event and queue the smallest sync needed."""

    source = await db.get(IntegrationSource, source_id)
    if not source or not source.is_active:
        raise HTTPException(status_code=404, detail="Webhook no encontrado")
    content_length = request.headers.get("content-length")
    try:
        if content_length and int(content_length) > 1024 * 1024:
            raise HTTPException(status_code=413, detail="El webhook supera el tamaño máximo permitido")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="El tamaño del webhook no es válido") from exc
    body = await request.body()
    try:
        details = verify_webhook_event(source, body, request.headers)
    except IntegrationRequestError as exc:
        raise HTTPException(status_code=exc.status_code or 400, detail=str(exc)) from exc

    event = IntegrationWebhookEvent(
        company_id=source.company_id,
        source_id=source.id,
        event_key=details["event_key"],
        event_type=details["event_type"],
        sync_type=details["sync_type"],
        status="RECEIVED",
        payload_hash=details["payload_hash"],
    )
    # Keeping the object construction explicit makes it clear that the raw
    # webhook body is never persisted. BaseModel supplies the UUID.
    db.add(event)
    try:
        await db.flush()
    except IntegrityError:
        await db.rollback()
        existing = (await db.execute(
            select(IntegrationWebhookEvent).where(
                IntegrationWebhookEvent.source_id == source.id,
                IntegrationWebhookEvent.event_key == details["event_key"],
            ).limit(1)
        )).scalars().first()
        if not existing:
            raise HTTPException(status_code=409, detail="No se pudo registrar el evento webhook")
        return {
            "accepted": True,
            "duplicate": True,
            "status": existing.status,
            "event_id": details.get("event_id"),
            "event_type": existing.event_type,
            "sync_type": existing.sync_type,
            "sync_run_id": existing.sync_run_id,
        }

    try:
        run = await enqueue_sync(
            db,
            source,
            None,
            sync_type=details["sync_type"],
            trigger_type="WEBHOOK",
        )
        event.sync_run_id = run.id
        event.status = "QUEUED"
        await db.commit()
        return {
            "accepted": True,
            "duplicate": False,
            "status": event.status,
            "event_id": details.get("event_id"),
            "event_type": event.event_type,
            "sync_type": event.sync_type,
            "sync_run_id": event.sync_run_id,
        }
    except IntegrationSyncConflict:
        # A polling/manual run already covers this event. Keep the event as a
        # durable audit record without creating a second concurrent run.
        event.status = "COALESCED"
        event.error_message = "La sincronización equivalente ya estaba en cola o en ejecución."
        await db.commit()
        return {
            "accepted": True,
            "duplicate": False,
            "status": event.status,
            "event_id": details.get("event_id"),
            "event_type": event.event_type,
            "sync_type": event.sync_type,
            "sync_run_id": None,
        }


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
