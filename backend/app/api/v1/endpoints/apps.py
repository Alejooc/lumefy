import asyncio
import json
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, List
from urllib import error as urlerror
from urllib import request as urlrequest

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import auth
from app.core.app_registry import APP_REGISTRY
from app.core.app_security import (
    api_key_prefix,
    generate_client_id,
    generate_client_secret,
    generate_api_key,
    generate_webhook_secret,
    hash_api_key,
    sign_webhook_payload,
)
from app.core.database import get_db
from app.core.permissions import PermissionChecker
from app.models.app_definition import AppDefinition
from app.models.app_install_event import AppInstallEvent
from app.models.app_webhook_delivery import AppWebhookDelivery
from app.models.company_app_install import CompanyAppInstall
from app.models.user import User
from app.schemas import app_marketplace as schemas

router = APIRouter()


def _unique(values: list[str]) -> list[str]:
    seen: set[str] = set()
    output: list[str] = []
    for value in values:
        if value not in seen:
            seen.add(value)
            output.append(value)
    return output


def _resolve_granted_scopes(app: AppDefinition, payload: schemas.AppInstallRequest) -> list[str]:
    requested_scopes = app.requested_scopes or []
    granted_scopes = payload.granted_scopes or requested_scopes
    missing = [scope for scope in requested_scopes if scope not in granted_scopes]
    if missing:
        raise HTTPException(
            status_code=422,
            detail=f"Faltan scopes requeridos para instalar la app: {', '.join(missing)}",
        )
    return _unique(granted_scopes)


def _has_capability(app: AppDefinition, capability: str) -> bool:
    return capability in (app.capabilities or [])


def _require_capability(app: AppDefinition, capability: str, action_label: str) -> None:
    if not _has_capability(app, capability):
        raise HTTPException(status_code=400, detail=f"La app '{app.slug}' no soporta {action_label}.")


def _next_invoice_date(install: CompanyAppInstall, app: AppDefinition) -> datetime | None:
    if app.pricing_model not in {"paid", "subscription"}:
        return None
    start = install.installed_at or datetime.utcnow()
    return start + timedelta(days=30)


def _serialize_install(
    install: CompanyAppInstall,
    app: AppDefinition,
    new_api_key: str | None = None,
) -> dict[str, Any]:
    return {
        "install_id": install.id,
        "app_id": app.id,
        "slug": app.slug,
        "name": app.name,
        "is_enabled": install.is_enabled,
        "installed_version": install.installed_version,
        "granted_scopes": install.granted_scopes or [],
        "api_key_prefix": install.api_key_prefix,
        "oauth_client_id": install.oauth_client_id,
        "webhook_url": install.webhook_url,
        "billing_status": install.billing_status or "active",
        "new_api_key": new_api_key,
        "settings": install.settings or {},
        "installed_at": install.installed_at,
    }


async def _log_install_event(
    db: AsyncSession,
    company_id: Any,
    app_id: Any,
    event_type: str,
    triggered_by_user_id: Any,
    payload: dict | None = None,
) -> None:
    db.add(
        AppInstallEvent(
            company_id=company_id,
            app_id=app_id,
            event_type=event_type,
            payload=payload or {},
            triggered_by_user_id=triggered_by_user_id,
        )
    )


def _post_webhook_sync(endpoint: str, body: bytes, headers: dict[str, str]) -> tuple[bool, int | None, str | None]:
    req = urlrequest.Request(endpoint, data=body, headers=headers, method="POST")
    try:
        with urlrequest.urlopen(req, timeout=8) as response:
            status_code = response.getcode()
            return 200 <= status_code < 300, status_code, None
    except urlerror.HTTPError as exc:
        return False, exc.code, f"http_error:{exc.code}"
    except Exception as exc:  # pragma: no cover - defensive fallback
        return False, None, str(exc)


async def _dispatch_signed_webhook(
    db: AsyncSession,
    install: CompanyAppInstall,
    app: AppDefinition,
    company_id: Any,
    event_name: str,
    payload: dict[str, Any],
    attempt_number: int = 1,
) -> dict[str, Any]:
    endpoint = install.webhook_url or (install.settings or {}).get("webhook_url")
    if not endpoint:
        return {"delivered": False, "reason": "webhook_url_missing"}
    if not install.webhook_secret:
        return {"delivered": False, "reason": "webhook_secret_missing", "endpoint": endpoint}

    envelope = {
        "event": event_name,
        "app_slug": app.slug,
        "company_id": str(company_id),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "payload": payload,
    }
    body = json.dumps(envelope, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    signature = sign_webhook_payload(install.webhook_secret, body)
    headers = {
        "Content-Type": "application/json",
        "X-Lumefy-Event": event_name,
        "X-Lumefy-Signature": signature,
    }

    delivered, status_code, reason = await asyncio.to_thread(_post_webhook_sync, endpoint, body, headers)
    delivery = AppWebhookDelivery(
        company_id=company_id,
        app_id=app.id,
        install_id=install.id,
        event_name=event_name,
        endpoint=endpoint,
        request_payload=envelope,
        signature=signature,
        success=delivered,
        status_code=status_code,
        error_message=reason,
        attempt_number=attempt_number,
    )
    db.add(delivery)
    await db.flush()
    return {
        "delivered": delivered,
        "endpoint": endpoint,
        "status_code": status_code,
        "signature": signature,
        "reason": reason,
        "delivery_id": str(delivery.id),
    }


async def _load_install_by_slug(
    db: AsyncSession,
    company_id: Any,
    slug: str,
) -> tuple[CompanyAppInstall, AppDefinition]:
    result = await db.execute(
        select(CompanyAppInstall, AppDefinition)
        .join(AppDefinition, AppDefinition.id == CompanyAppInstall.app_id)
        .where(CompanyAppInstall.company_id == company_id, AppDefinition.slug == slug)
    )
    row = result.first()
    if not row:
        raise HTTPException(status_code=404, detail="La app no esta instalada")
    return row


async def ensure_default_apps(db: AsyncSession) -> None:
    result = await db.execute(select(AppDefinition))
    existing_apps = {app.slug: app for app in result.scalars().all()}
    changed = False

    for item in APP_REGISTRY:
        existing = existing_apps.get(item["slug"])
        if existing:
            for field, value in item.items():
                current_value = getattr(existing, field, None)
                if field == "config_schema" and isinstance(current_value, dict) and isinstance(value, dict):
                    merged_schema = dict(current_value)
                    target_properties = (value.get("properties") or {}) if isinstance(value.get("properties"), dict) else {}
                    current_properties = (merged_schema.get("properties") or {}) if isinstance(merged_schema.get("properties"), dict) else {}
                    schema_changed = False

                    for p_key, p_value in target_properties.items():
                        if p_key not in current_properties:
                            current_properties[p_key] = p_value
                            schema_changed = True
                    if schema_changed:
                        merged_schema["properties"] = current_properties

                    for top_key, top_value in value.items():
                        if top_key == "properties":
                            continue
                        if top_key not in merged_schema:
                            merged_schema[top_key] = top_value
                            schema_changed = True

                    if schema_changed:
                        setattr(existing, field, merged_schema)
                        changed = True
                    continue

                if field == "default_config" and isinstance(current_value, dict) and isinstance(value, dict):
                    merged_defaults = dict(current_value)
                    defaults_changed = False
                    for conf_key, conf_value in value.items():
                        if conf_key not in merged_defaults:
                            merged_defaults[conf_key] = conf_value
                            defaults_changed = True
                    if defaults_changed:
                        setattr(existing, field, merged_defaults)
                        changed = True
                    continue

                if field in {"requested_scopes", "capabilities"} and isinstance(current_value, list) and isinstance(value, list):
                    merged_list = list(current_value)
                    list_changed = False
                    for item_value in value:
                        if item_value not in merged_list:
                            merged_list.append(item_value)
                            list_changed = True
                    if list_changed:
                        setattr(existing, field, merged_list)
                        changed = True
                    continue

                if current_value in (None, "", [], {}):
                    setattr(existing, field, value)
                    changed = True
            continue
        db.add(AppDefinition(**item))
        changed = True

    if changed:
        await db.commit()


def ensure_superuser(user: User) -> None:
    if not user.is_superuser:
        raise HTTPException(status_code=403, detail="Solo super admin puede gestionar catalogo global de apps")


@router.get("/catalog", response_model=List[schemas.AppCatalogItem])
async def list_catalog(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(PermissionChecker("manage_company")),
) -> Any:
    await ensure_default_apps(db)

    apps_result = await db.execute(
        select(AppDefinition)
        .where(AppDefinition.is_active == True, AppDefinition.is_listed == True)
        .order_by(AppDefinition.name.asc())
    )
    apps = apps_result.scalars().all()

    installed_map: dict[str, CompanyAppInstall] = {}
    if current_user.company_id:
        installs_result = await db.execute(
            select(CompanyAppInstall).where(CompanyAppInstall.company_id == current_user.company_id)
        )
        installs = installs_result.scalars().all()
        installed_map = {str(i.app_id): i for i in installs}

    return [
        {
            "id": app.id,
            "slug": app.slug,
            "name": app.name,
            "description": app.description,
            "category": app.category,
            "version": app.version,
            "icon": app.icon,
            "is_active": app.is_active,
            "is_listed": app.is_listed,
            "requested_scopes": app.requested_scopes or [],
            "capabilities": app.capabilities or [],
            "pricing_model": app.pricing_model or "free",
            "monthly_price": float(app.monthly_price or 0),
            "setup_url": app.setup_url,
            "docs_url": app.docs_url,
            "support_url": app.support_url,
            "installed": str(app.id) in installed_map,
            "is_enabled": installed_map[str(app.id)].is_enabled if str(app.id) in installed_map else False,
            "config_schema": app.config_schema or {},
        }
        for app in apps
    ]


@router.get("/admin/catalog", response_model=List[schemas.AppDefinitionOut])
async def admin_list_catalog(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(auth.get_current_user),
) -> Any:
    ensure_superuser(current_user)
    await ensure_default_apps(db)
    result = await db.execute(select(AppDefinition).order_by(AppDefinition.name.asc()))
    apps = result.scalars().all()
    return [
        {
            "id": app.id,
            "slug": app.slug,
            "name": app.name,
            "description": app.description,
            "category": app.category,
            "version": app.version,
            "icon": app.icon,
            "requested_scopes": app.requested_scopes or [],
            "capabilities": app.capabilities or [],
            "config_schema": app.config_schema or {},
            "default_config": app.default_config or {},
            "setup_url": app.setup_url,
            "docs_url": app.docs_url,
            "support_url": app.support_url,
            "pricing_model": app.pricing_model or "free",
            "monthly_price": float(app.monthly_price or 0),
            "is_listed": app.is_listed,
            "is_active": app.is_active,
        }
        for app in apps
    ]


@router.post("/admin/catalog", response_model=schemas.AppDefinitionOut)
async def admin_create_app(
    payload: schemas.AppDefinitionCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(auth.get_current_user),
) -> Any:
    ensure_superuser(current_user)
    slug = payload.slug.strip().lower()
    result = await db.execute(select(AppDefinition).where(AppDefinition.slug == slug))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Ya existe una app con ese slug")

    app = AppDefinition(
        slug=slug,
        name=payload.name,
        description=payload.description,
        category=payload.category,
        version=payload.version,
        icon=payload.icon,
        requested_scopes=payload.requested_scopes,
        capabilities=payload.capabilities,
        config_schema=payload.config_schema,
        default_config=payload.default_config,
        setup_url=payload.setup_url,
        docs_url=payload.docs_url,
        support_url=payload.support_url,
        pricing_model=payload.pricing_model,
        monthly_price=payload.monthly_price,
        is_listed=payload.is_listed,
        is_active=payload.is_active,
    )
    db.add(app)
    await db.commit()
    await db.refresh(app)
    return app


@router.put("/admin/catalog/{slug}", response_model=schemas.AppDefinitionOut)
async def admin_update_app(
    slug: str,
    payload: schemas.AppDefinitionUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(auth.get_current_user),
) -> Any:
    ensure_superuser(current_user)
    result = await db.execute(select(AppDefinition).where(AppDefinition.slug == slug))
    app = result.scalar_one_or_none()
    if not app:
        raise HTTPException(status_code=404, detail="App no encontrada")

    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(app, field, value)

    await db.commit()
    await db.refresh(app)
    return app


@router.get("/installed", response_model=List[schemas.AppInstallOut])
async def list_installed(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(PermissionChecker("manage_company")),
) -> Any:
    await ensure_default_apps(db)
    if not current_user.company_id:
        return []

    result = await db.execute(
        select(CompanyAppInstall, AppDefinition)
        .join(AppDefinition, AppDefinition.id == CompanyAppInstall.app_id)
        .where(CompanyAppInstall.company_id == current_user.company_id)
        .order_by(AppDefinition.name.asc())
    )
    rows = result.all()
    return [_serialize_install(install, app) for install, app in rows]


@router.get("/installed/{slug}", response_model=schemas.AppInstalledDetail)
async def get_installed_detail(
    slug: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(PermissionChecker("manage_company")),
) -> Any:
    await ensure_default_apps(db)
    if not current_user.company_id:
        raise HTTPException(status_code=400, detail="El usuario no tiene company_id asociado")

    install, app = await _load_install_by_slug(db, current_user.company_id, slug)
    if not install.is_enabled:
        raise HTTPException(status_code=404, detail="La app no esta instalada/activa")

    return {
        **_serialize_install(install, app),
        "description": app.description,
        "category": app.category,
        "version": app.version,
        "icon": app.icon,
        "config_schema": app.config_schema or {},
        "default_config": app.default_config or {},
        "requested_scopes": app.requested_scopes or [],
        "capabilities": app.capabilities or [],
        "setup_url": app.setup_url,
        "docs_url": app.docs_url,
        "support_url": app.support_url,
        "pricing_model": app.pricing_model or "free",
        "monthly_price": float(app.monthly_price or 0),
    }


@router.get("/installed/{slug}/events", response_model=List[schemas.AppInstallEventOut])
async def get_installed_events(
    slug: str,
    limit: int = 20,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(PermissionChecker("manage_company")),
) -> Any:
    if not current_user.company_id:
        return []

    app_result = await db.execute(select(AppDefinition).where(AppDefinition.slug == slug))
    app = app_result.scalar_one_or_none()
    if not app:
        raise HTTPException(status_code=404, detail="App no encontrada")

    result = await db.execute(
        select(AppInstallEvent)
        .where(AppInstallEvent.company_id == current_user.company_id, AppInstallEvent.app_id == app.id)
        .order_by(AppInstallEvent.created_at.desc())
        .limit(max(1, min(limit, 100)))
    )
    events = result.scalars().all()
    return [
        {
            "id": event.id,
            "event_type": event.event_type,
            "payload": event.payload or {},
            "created_at": event.created_at,
            "triggered_by_user_id": event.triggered_by_user_id,
        }
        for event in events
    ]


@router.get("/installed/{slug}/billing", response_model=schemas.AppBillingSummary)
async def get_billing_summary(
    slug: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(PermissionChecker("manage_company")),
) -> Any:
    if not current_user.company_id:
        raise HTTPException(status_code=400, detail="El usuario no tiene company_id asociado")
    install, app = await _load_install_by_slug(db, current_user.company_id, slug)
    return {
        "slug": app.slug,
        "name": app.name,
        "pricing_model": app.pricing_model or "free",
        "monthly_price": float(app.monthly_price or 0),
        "currency": "USD",
        "billing_status": install.billing_status or "active",
        "is_enabled": install.is_enabled,
        "next_invoice_date": _next_invoice_date(install, app),
    }


@router.post("/installed/{slug}/rotate-api-key", response_model=schemas.RotateApiKeyOut)
async def rotate_api_key(
    slug: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(PermissionChecker("manage_company")),
) -> Any:
    if not current_user.company_id:
        raise HTTPException(status_code=400, detail="El usuario no tiene company_id asociado")
    install, app = await _load_install_by_slug(db, current_user.company_id, slug)

    new_key = generate_api_key()
    install.api_key_prefix = api_key_prefix(new_key)
    install.api_key_hash = hash_api_key(new_key)

    await _log_install_event(
        db=db,
        company_id=current_user.company_id,
        app_id=app.id,
        event_type="api_key_rotated",
        triggered_by_user_id=current_user.id,
        payload={"api_key_prefix": install.api_key_prefix},
    )
    await db.commit()
    return {
        "api_key_prefix": install.api_key_prefix,
        "new_api_key": new_key,
        "rotated_at": datetime.utcnow(),
    }


@router.post("/installed/{slug}/rotate-webhook-secret", response_model=schemas.RotateWebhookSecretOut)
async def rotate_webhook_secret(
    slug: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(PermissionChecker("manage_company")),
) -> Any:
    if not current_user.company_id:
        raise HTTPException(status_code=400, detail="El usuario no tiene company_id asociado")
    install, app = await _load_install_by_slug(db, current_user.company_id, slug)
    _require_capability(app, "webhook_consumer", "webhooks")

    install.webhook_secret = generate_webhook_secret()
    await _log_install_event(
        db=db,
        company_id=current_user.company_id,
        app_id=app.id,
        event_type="webhook_secret_rotated",
        triggered_by_user_id=current_user.id,
        payload={},
    )
    await db.commit()
    return {"webhook_secret": install.webhook_secret, "rotated_at": datetime.utcnow()}


@router.post("/installed/{slug}/rotate-client-secret", response_model=schemas.RotateClientSecretOut)
async def rotate_client_secret(
    slug: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(PermissionChecker("manage_company")),
) -> Any:
    if not current_user.company_id:
        raise HTTPException(status_code=400, detail="El usuario no tiene company_id asociado")
    install, app = await _load_install_by_slug(db, current_user.company_id, slug)
    _require_capability(app, "external_api", "credenciales de cliente")

    new_client_secret = generate_client_secret()
    install.oauth_client_id = install.oauth_client_id or generate_client_id()
    install.oauth_client_secret_hash = hash_api_key(new_client_secret)
    await _log_install_event(
        db=db,
        company_id=current_user.company_id,
        app_id=app.id,
        event_type="client_secret_rotated",
        triggered_by_user_id=current_user.id,
        payload={"oauth_client_id": install.oauth_client_id},
    )
    await db.commit()
    return {
        "oauth_client_id": install.oauth_client_id,
        "new_client_secret": new_client_secret,
        "rotated_at": datetime.utcnow(),
    }


@router.get("/installed/{slug}/webhooks/deliveries", response_model=List[schemas.WebhookDeliveryOut])
async def get_webhook_deliveries(
    slug: str,
    limit: int = 25,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(PermissionChecker("manage_company")),
) -> Any:
    if not current_user.company_id:
        return []
    install, app = await _load_install_by_slug(db, current_user.company_id, slug)
    _require_capability(app, "webhook_consumer", "webhooks")
    result = await db.execute(
        select(AppWebhookDelivery)
        .where(AppWebhookDelivery.install_id == install.id)
        .order_by(AppWebhookDelivery.created_at.desc())
        .limit(max(1, min(limit, 100)))
    )
    deliveries = result.scalars().all()
    return [
        {
            "id": delivery.id,
            "event_name": delivery.event_name,
            "endpoint": delivery.endpoint,
            "success": delivery.success,
            "status_code": delivery.status_code,
            "error_message": delivery.error_message,
            "attempt_number": delivery.attempt_number,
            "created_at": delivery.created_at,
        }
        for delivery in deliveries
    ]


@router.post("/installed/{slug}/webhooks/deliveries/{delivery_id}/retry", response_model=schemas.WebhookTestOut)
async def retry_webhook_delivery(
    slug: str,
    delivery_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(PermissionChecker("manage_company")),
) -> Any:
    if not current_user.company_id:
        raise HTTPException(status_code=400, detail="El usuario no tiene company_id asociado")
    install, app = await _load_install_by_slug(db, current_user.company_id, slug)
    _require_capability(app, "webhook_consumer", "webhooks")
    try:
        delivery_uuid = uuid.UUID(delivery_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="delivery_id invalido") from exc

    query = await db.execute(
        select(AppWebhookDelivery).where(
            AppWebhookDelivery.id == delivery_uuid,
            AppWebhookDelivery.install_id == install.id,
        )
    )
    delivery = query.scalar_one_or_none()
    if not delivery:
        raise HTTPException(status_code=404, detail="Entrega webhook no encontrada")

    next_attempt = max(1, int(delivery.attempt_number or 1) + 1)
    payload = (delivery.request_payload or {}).get("payload") or {}
    result = await _dispatch_signed_webhook(
        db=db,
        install=install,
        app=app,
        company_id=current_user.company_id,
        event_name=delivery.event_name,
        payload=payload,
        attempt_number=next_attempt,
    )
    await _log_install_event(
        db=db,
        company_id=current_user.company_id,
        app_id=app.id,
        event_type="webhook_retry",
        triggered_by_user_id=current_user.id,
        payload={"delivery_id": delivery_id, **result},
    )
    await db.commit()
    return result


@router.post("/installed/{slug}/webhooks/test", response_model=schemas.WebhookTestOut)
async def send_test_webhook(
    slug: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(PermissionChecker("manage_company")),
) -> Any:
    if not current_user.company_id:
        raise HTTPException(status_code=400, detail="El usuario no tiene company_id asociado")
    install, app = await _load_install_by_slug(db, current_user.company_id, slug)
    _require_capability(app, "webhook_consumer", "webhooks")

    result = await _dispatch_signed_webhook(
        db=db,
        install=install,
        app=app,
        company_id=current_user.company_id,
        event_name="app.webhook_test",
        payload={"triggered_by": str(current_user.id)},
    )
    await _log_install_event(
        db=db,
        company_id=current_user.company_id,
        app_id=app.id,
        event_type="webhook_test",
        triggered_by_user_id=current_user.id,
        payload=result,
    )
    await db.commit()
    return result


@router.post("/install/{slug}", response_model=schemas.AppInstallOut)
async def install_app(
    slug: str,
    payload: schemas.AppInstallRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(PermissionChecker("manage_company")),
) -> Any:
    if not current_user.company_id:
        raise HTTPException(status_code=400, detail="El usuario no tiene company_id asociado")

    await ensure_default_apps(db)
    app_result = await db.execute(
        select(AppDefinition).where(AppDefinition.slug == slug, AppDefinition.is_active == True)
    )
    app = app_result.scalar_one_or_none()
    if not app:
        raise HTTPException(status_code=404, detail="App no encontrada")

    granted_scopes = _resolve_granted_scopes(app, payload)
    install_result = await db.execute(
        select(CompanyAppInstall).where(
            CompanyAppInstall.company_id == current_user.company_id,
            CompanyAppInstall.app_id == app.id,
        )
    )
    install = install_result.scalar_one_or_none()
    installed_version = payload.target_version or app.version
    generated_api_key: str | None = None
    generated_client_secret: str | None = None

    if install:
        install.is_enabled = True
        install.installed_version = installed_version
        install.granted_scopes = granted_scopes
        if not install.api_key_hash:
            generated_api_key = generate_api_key()
            install.api_key_prefix = api_key_prefix(generated_api_key)
            install.api_key_hash = hash_api_key(generated_api_key)
        if not install.webhook_secret:
            if _has_capability(app, "webhook_consumer"):
                install.webhook_secret = generate_webhook_secret()
        if (not install.oauth_client_id or not install.oauth_client_secret_hash) and _has_capability(app, "external_api"):
            generated_client_secret = generate_client_secret()
            install.oauth_client_id = install.oauth_client_id or generate_client_id()
            install.oauth_client_secret_hash = hash_api_key(generated_client_secret)
    else:
        generated_api_key = generate_api_key()
        generated_client_secret = generate_client_secret()
        install = CompanyAppInstall(
            company_id=current_user.company_id,
            app_id=app.id,
            is_enabled=True,
            installed_version=installed_version,
            granted_scopes=granted_scopes,
            api_key_prefix=api_key_prefix(generated_api_key),
            api_key_hash=hash_api_key(generated_api_key),
            oauth_client_id=generate_client_id() if _has_capability(app, "external_api") else None,
            oauth_client_secret_hash=hash_api_key(generated_client_secret) if _has_capability(app, "external_api") else None,
            webhook_secret=generate_webhook_secret() if _has_capability(app, "webhook_consumer") else None,
            settings=app.default_config or {},
            installed_by_user_id=current_user.id,
        )
        db.add(install)

    await _log_install_event(
        db=db,
        company_id=current_user.company_id,
        app_id=app.id,
        event_type="install",
        triggered_by_user_id=current_user.id,
        payload={"granted_scopes": granted_scopes, "installed_version": installed_version},
    )
    await db.commit()
    await db.refresh(install)

    if _has_capability(app, "webhook_consumer"):
        webhook_result = await _dispatch_signed_webhook(
            db=db,
            install=install,
            app=app,
            company_id=current_user.company_id,
            event_name="app.installed",
            payload={"installed_version": install.installed_version},
        )
        await _log_install_event(
            db=db,
            company_id=current_user.company_id,
            app_id=app.id,
            event_type="webhook_dispatch",
            triggered_by_user_id=current_user.id,
            payload=webhook_result,
        )
        await db.commit()
    return _serialize_install(install, app, new_api_key=generated_api_key)


@router.post("/uninstall/{slug}", response_model=schemas.AppInstallOut)
async def uninstall_app(
    slug: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(PermissionChecker("manage_company")),
) -> Any:
    if not current_user.company_id:
        raise HTTPException(status_code=400, detail="El usuario no tiene company_id asociado")

    install, app = await _load_install_by_slug(db, current_user.company_id, slug)
    install.is_enabled = False
    await _log_install_event(
        db=db,
        company_id=current_user.company_id,
        app_id=app.id,
        event_type="uninstall",
        triggered_by_user_id=current_user.id,
        payload={"installed_version": install.installed_version},
    )
    await db.commit()
    await db.refresh(install)

    if _has_capability(app, "webhook_consumer"):
        webhook_result = await _dispatch_signed_webhook(
            db=db,
            install=install,
            app=app,
            company_id=current_user.company_id,
            event_name="app.uninstalled",
            payload={"installed_version": install.installed_version},
        )
        await _log_install_event(
            db=db,
            company_id=current_user.company_id,
            app_id=app.id,
            event_type="webhook_dispatch",
            triggered_by_user_id=current_user.id,
            payload=webhook_result,
        )
        await db.commit()
    return _serialize_install(install, app)


@router.put("/config/{slug}", response_model=schemas.AppInstallOut)
async def update_app_config(
    slug: str,
    payload: schemas.AppConfigUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(PermissionChecker("manage_company")),
) -> Any:
    if not current_user.company_id:
        raise HTTPException(status_code=400, detail="El usuario no tiene company_id asociado")

    install, app = await _load_install_by_slug(db, current_user.company_id, slug)
    install.settings = payload.settings
    if isinstance(payload.settings, dict):
        install.webhook_url = payload.settings.get("webhook_url") or install.webhook_url

    await _log_install_event(
        db=db,
        company_id=current_user.company_id,
        app_id=app.id,
        event_type="config_update",
        triggered_by_user_id=current_user.id,
        payload={"settings_keys": list((payload.settings or {}).keys())},
    )
    await db.commit()
    await db.refresh(install)

    if _has_capability(app, "webhook_consumer"):
        webhook_result = await _dispatch_signed_webhook(
            db=db,
            install=install,
            app=app,
            company_id=current_user.company_id,
            event_name="app.config_updated",
            payload={"settings_keys": list((payload.settings or {}).keys())},
        )
        await _log_install_event(
            db=db,
            company_id=current_user.company_id,
            app_id=app.id,
            event_type="webhook_dispatch",
            triggered_by_user_id=current_user.id,
            payload=webhook_result,
        )
        await db.commit()
    return _serialize_install(install, app)


@router.get("/demo/hello", response_model=schemas.DemoAppResponse)
async def run_demo_hello(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(auth.get_current_user),
) -> Any:
    if not current_user.company_id:
        raise HTTPException(status_code=400, detail="El usuario no tiene company_id asociado")

    result = await db.execute(
        select(CompanyAppInstall, AppDefinition)
        .join(AppDefinition, AppDefinition.id == CompanyAppInstall.app_id)
        .where(
            CompanyAppInstall.company_id == current_user.company_id,
            CompanyAppInstall.is_enabled == True,
            AppDefinition.slug == "demo-hello",
        )
    )
    row = result.first()
    if not row:
        raise HTTPException(status_code=400, detail="La app demo-hello no esta instalada/activa")

    install, app = row
    welcome = (install.settings or {}).get("welcome_message") or "Hola desde Demo Hello App"
    return {
        "app_slug": app.slug,
        "message": f"App '{app.name}' ejecutada correctamente para la empresa.",
        "configured_message": welcome,
    }
