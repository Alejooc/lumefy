from typing import Any, List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.permissions import PermissionChecker
from app.core import auth
from app.models.user import User
from app.models.app_definition import AppDefinition
from app.models.company_app_install import CompanyAppInstall
from app.schemas import app_marketplace as schemas

router = APIRouter()

DEFAULT_APPS = [
    {
        "slug": "demo-hello",
        "name": "Demo Hello App",
        "description": "App base de ejemplo para aprender como crear nuevas integraciones.",
        "category": "Productividad",
        "version": "1.0.0",
        "icon": "rocket",
        "config_schema": {
            "welcome_message": "string",
            "accent_color": "string"
        },
        "default_config": {
            "welcome_message": "Hola desde tu primera app de Lumefy",
            "accent_color": "#4680ff"
        }
    }
]


async def ensure_default_apps(db: AsyncSession) -> None:
    result = await db.execute(select(AppDefinition.slug))
    existing_slugs = {row[0] for row in result.fetchall()}

    created = False
    for item in DEFAULT_APPS:
        if item["slug"] in existing_slugs:
            continue
        db.add(AppDefinition(**item))
        created = True

    if created:
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
        select(AppDefinition).where(AppDefinition.is_active == True).order_by(AppDefinition.name.asc())
    )
    apps = apps_result.scalars().all()

    installed_map = {}
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
            "installed": str(app.id) in installed_map,
            "is_enabled": installed_map[str(app.id)].is_enabled if str(app.id) in installed_map else False,
            "config_schema": app.config_schema or {}
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
            "config_schema": app.config_schema or {},
            "default_config": app.default_config or {},
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
        config_schema=payload.config_schema,
        default_config=payload.default_config,
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
    if not current_user.company_id:
        return []

    result = await db.execute(
        select(CompanyAppInstall, AppDefinition)
        .join(AppDefinition, AppDefinition.id == CompanyAppInstall.app_id)
        .where(CompanyAppInstall.company_id == current_user.company_id)
        .order_by(AppDefinition.name.asc())
    )
    rows = result.all()

    return [
        {
            "install_id": install.id,
            "app_id": app.id,
            "slug": app.slug,
            "name": app.name,
            "is_enabled": install.is_enabled,
            "settings": install.settings or {},
            "installed_at": install.installed_at
        }
        for install, app in rows
    ]


@router.get("/installed/{slug}", response_model=schemas.AppInstalledDetail)
async def get_installed_detail(
    slug: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(PermissionChecker("manage_company")),
) -> Any:
    if not current_user.company_id:
        raise HTTPException(status_code=400, detail="El usuario no tiene company_id asociado")

    result = await db.execute(
        select(CompanyAppInstall, AppDefinition)
        .join(AppDefinition, AppDefinition.id == CompanyAppInstall.app_id)
        .where(
            CompanyAppInstall.company_id == current_user.company_id,
            CompanyAppInstall.is_enabled == True,
            AppDefinition.slug == slug
        )
    )
    row = result.first()
    if not row:
        raise HTTPException(status_code=404, detail="La app no esta instalada/activa")

    install, app = row
    return {
        "install_id": install.id,
        "app_id": app.id,
        "slug": app.slug,
        "name": app.name,
        "description": app.description,
        "category": app.category,
        "version": app.version,
        "is_enabled": install.is_enabled,
        "settings": install.settings or {},
        "config_schema": app.config_schema or {},
        "installed_at": install.installed_at
    }


@router.post("/install/{slug}", response_model=schemas.AppInstallOut)
async def install_app(
    slug: str,
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

    install_result = await db.execute(
        select(CompanyAppInstall).where(
            CompanyAppInstall.company_id == current_user.company_id,
            CompanyAppInstall.app_id == app.id
        )
    )
    install = install_result.scalar_one_or_none()

    if install:
        install.is_enabled = True
    else:
        install = CompanyAppInstall(
            company_id=current_user.company_id,
            app_id=app.id,
            is_enabled=True,
            settings=app.default_config or {},
            installed_by_user_id=current_user.id
        )
        db.add(install)

    await db.commit()
    await db.refresh(install)

    return {
        "install_id": install.id,
        "app_id": app.id,
        "slug": app.slug,
        "name": app.name,
        "is_enabled": install.is_enabled,
        "settings": install.settings or {},
        "installed_at": install.installed_at
    }


@router.post("/uninstall/{slug}", response_model=schemas.AppInstallOut)
async def uninstall_app(
    slug: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(PermissionChecker("manage_company")),
) -> Any:
    if not current_user.company_id:
        raise HTTPException(status_code=400, detail="El usuario no tiene company_id asociado")

    result = await db.execute(
        select(CompanyAppInstall, AppDefinition)
        .join(AppDefinition, AppDefinition.id == CompanyAppInstall.app_id)
        .where(
            CompanyAppInstall.company_id == current_user.company_id,
            AppDefinition.slug == slug
        )
    )
    row = result.first()
    if not row:
        raise HTTPException(status_code=404, detail="La app no esta instalada")

    install, app = row
    install.is_enabled = False
    await db.commit()
    await db.refresh(install)

    return {
        "install_id": install.id,
        "app_id": app.id,
        "slug": app.slug,
        "name": app.name,
        "is_enabled": install.is_enabled,
        "settings": install.settings or {},
        "installed_at": install.installed_at
    }


@router.put("/config/{slug}", response_model=schemas.AppInstallOut)
async def update_app_config(
    slug: str,
    payload: schemas.AppConfigUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(PermissionChecker("manage_company")),
) -> Any:
    if not current_user.company_id:
        raise HTTPException(status_code=400, detail="El usuario no tiene company_id asociado")

    result = await db.execute(
        select(CompanyAppInstall, AppDefinition)
        .join(AppDefinition, AppDefinition.id == CompanyAppInstall.app_id)
        .where(
            CompanyAppInstall.company_id == current_user.company_id,
            AppDefinition.slug == slug
        )
    )
    row = result.first()
    if not row:
        raise HTTPException(status_code=404, detail="La app no esta instalada")

    install, app = row
    install.settings = payload.settings
    await db.commit()
    await db.refresh(install)

    return {
        "install_id": install.id,
        "app_id": app.id,
        "slug": app.slug,
        "name": app.name,
        "is_enabled": install.is_enabled,
        "settings": install.settings or {},
        "installed_at": install.installed_at
    }


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
            AppDefinition.slug == "demo-hello"
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
        "configured_message": welcome
    }
