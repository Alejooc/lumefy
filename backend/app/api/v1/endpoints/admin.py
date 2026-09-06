from typing import Any, List
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func, or_, select
from app.core.database import get_db
from app.models.company import Company
from app.models.user import User
from app.models.branch import Branch
from app.models.warehouse import Warehouse
from app.models.role import Role
from app.models.plan import Plan
from app.models.saas_billing import SaaSBillingRecord
from app.models.system_setting import SystemSetting
from app.schemas import system_setting as setting_schemas
from app.schemas import company as schemas
from app.schemas import saas_billing as billing_schemas
from app.core.permissions import PermissionChecker
from app.core.security import get_password_hash
import uuid

# This router should be protected. 
# For now we use a permission 'manage_saas' which superusers should have by default.
# Or we can check current_user.is_superuser

router = APIRouter()


def _subscription_is_current(*, is_active: bool, status: str | None, valid_until: str | None) -> bool:
    """Return whether a tenant currently contributes to contracted MRR."""

    if not is_active or (status or "ACTIVE").strip().upper() not in {"ACTIVE", "PAST_DUE"}:
        return False
    if not valid_until:
        return True
    raw_expiry = str(valid_until).strip()
    try:
        expiry = datetime.fromisoformat(raw_expiry.replace("Z", "+00:00"))
    except ValueError:
        # An invalid legacy value must not make a tenant look billable forever.
        return False
    if expiry.tzinfo is None:
        expiry = expiry.replace(tzinfo=timezone.utc)
    if len(raw_expiry) == 10 and "T" not in raw_expiry and " " not in raw_expiry:
        expiry = expiry.replace(hour=23, minute=59, second=59, microsecond=999999)
    return expiry >= datetime.now(timezone.utc)


def _plan_monthly_price(plan: Plan) -> float:
    """Normalize a plan price to a 30-day equivalent for estimated MRR."""

    price = max(float(plan.price or 0), 0.0)
    duration_days = max(int(plan.duration_days or 30), 1)
    return price * 30 / duration_days


async def _resolve_active_plan(db: AsyncSession, plan_code: str | None) -> Plan:
    normalized_code = (plan_code or "").strip().upper()
    if not normalized_code:
        raise HTTPException(status_code=422, detail="Debes seleccionar un plan activo para la empresa")

    plan = await db.scalar(
        select(Plan).where(func.upper(Plan.code) == normalized_code, Plan.is_active.is_(True))
    )
    if not plan:
        raise HTTPException(status_code=422, detail="El plan seleccionado no existe o está inactivo")
    return plan


def _parse_subscription_expiry(value: str | None) -> datetime | None:
    if not value:
        return None
    raw_expiry = str(value).strip()
    try:
        expiry = datetime.fromisoformat(raw_expiry.replace("Z", "+00:00"))
    except ValueError:
        return None
    if expiry.tzinfo is None:
        expiry = expiry.replace(tzinfo=timezone.utc)
    if len(raw_expiry) == 10 and "T" not in raw_expiry and " " not in raw_expiry:
        expiry = expiry.replace(hour=23, minute=59, second=59, microsecond=999999)
    return expiry


def _billing_state(
    *,
    valid_until: str | None,
    latest_record: SaaSBillingRecord | None,
    now: datetime | None = None,
) -> str:
    """Classify a tenant for the SaaS billing portfolio."""

    now = now or datetime.now(timezone.utc)
    if latest_record and latest_record.status == "PENDING":
        return "PENDING"
    expiry = _parse_subscription_expiry(valid_until)
    if expiry and expiry < now:
        return "OVERDUE"
    if expiry and expiry <= now + timedelta(days=7):
        return "DUE_SOON"
    if latest_record and latest_record.status == "PAID":
        return "PAID"
    return "NO_RECORD"

@router.get("/settings", response_model=List[setting_schemas.SystemSetting])
async def read_settings(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(PermissionChecker("manage_saas")),
) -> Any:
    """
    Get all system settings.
    """
    result = await db.execute(select(SystemSetting))
    return result.scalars().all()

@router.put("/settings/bulk", response_model=List[setting_schemas.SystemSetting])
async def update_settings_bulk(
    *,
    db: AsyncSession = Depends(get_db),
    settings_in: List[setting_schemas.SystemSettingCreate], # Using Create schema but mostly for key/value
    current_user: User = Depends(PermissionChecker("manage_saas")),
) -> Any:
    """
    Update multiple settings at once (Upsert).
    """
    updated_settings = []
    for setting_in in settings_in:
        # Check if exists
        result = await db.execute(select(SystemSetting).where(SystemSetting.key == setting_in.key))
        existing = result.scalars().first()
        
        if existing:
            existing.value = setting_in.value
            if setting_in.group: existing.group = setting_in.group
            if setting_in.is_public is not None: existing.is_public = setting_in.is_public
            db.add(existing)
            updated_settings.append(existing)
        else:
            new_setting = SystemSetting(
                key=setting_in.key,
                value=setting_in.value,
                group=setting_in.group,
                is_public=setting_in.is_public,
                description=setting_in.description
            )
            db.add(new_setting)
            updated_settings.append(new_setting)
            
    await db.commit()
    return updated_settings

@router.get("/settings/public", response_model=List[setting_schemas.SystemSetting])
async def read_public_settings(
    db: AsyncSession = Depends(get_db),
) -> Any:
    """
    Get public settings (e.g. Branding) - No Auth required.
    """
    result = await db.execute(select(SystemSetting).where(SystemSetting.is_public == True))
    return result.scalars().all()

# ... existing companies code ...

# This router should be protected. 
# For now we use a permission 'manage_saas' which superusers should have by default.
# Or we can check current_user.is_superuser

# Router already defined above
# router = APIRouter()

@router.get("/stats")
async def read_admin_stats(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(PermissionChecker("manage_saas")),
) -> Any:
    """
    Get SaaS Statistics (KPIs).
    """
    company_result = await db.execute(
        select(Company.plan, Company.subscription_status, Company.valid_until, Company.is_active)
    )
    company_rows = company_result.all()
    total_companies = len(company_rows)
    active_companies = sum(1 for row in company_rows if bool(row.is_active))

    # Total Users
    result = await db.execute(
        select(func.count(User.id)).where(
            or_(User.role_id.is_not(None), User.is_superuser == True)
        )
    )
    total_users = result.scalar() or 0

    plans_result = await db.execute(select(Plan))
    plans_by_code = {
        (plan.code or "").strip().upper(): plan
        for plan in plans_result.scalars().all()
        if (plan.code or "").strip()
    }
    active_subscriptions: dict[str, int] = {}
    status_counts: dict[str, int] = {}
    mrr_by_currency: dict[str, float] = {}
    unpriced_active_subscriptions = 0
    paid_subscription_count = 0

    for row in company_rows:
        status = (row.subscription_status or "ACTIVE").strip().upper()
        status_counts[status] = status_counts.get(status, 0) + 1
        if not _subscription_is_current(
            is_active=bool(row.is_active),
            status=status,
            valid_until=row.valid_until,
        ):
            continue

        plan_code = (row.plan or "UNMAPPED").strip().upper() or "UNMAPPED"
        active_subscriptions[plan_code] = active_subscriptions.get(plan_code, 0) + 1
        plan = plans_by_code.get(plan_code)
        if not plan:
            unpriced_active_subscriptions += 1
            continue
        if float(plan.price or 0) > 0:
            paid_subscription_count += 1
        currency = (plan.currency or "USD").strip().upper() or "USD"
        mrr_by_currency[currency] = mrr_by_currency.get(currency, 0.0) + _plan_monthly_price(plan)

    mrr_by_currency = {currency: round(value, 2) for currency, value in mrr_by_currency.items()}
    currencies = sorted(mrr_by_currency)
    display_currency = currencies[0] if len(currencies) == 1 else None
    # Keep the legacy numeric field for existing clients. It is only a valid
    # total when all contracted plans use one currency; the complete breakdown
    # is available in mrr_by_currency.
    mrr = mrr_by_currency.get(display_currency, 0.0) if display_currency else 0.0

    return {
        "total_companies": total_companies,
        "active_companies": active_companies,
        "total_users": total_users,
        "mrr": mrr,
        "mrr_currency": display_currency,
        "mrr_by_currency": mrr_by_currency,
        "mrr_is_estimate": True,
        "unpriced_active_subscriptions": unpriced_active_subscriptions,
        "active_subscription_count": sum(active_subscriptions.values()),
        "paid_subscription_count": paid_subscription_count,
        "active_subscriptions": active_subscriptions,
        "subscription_statuses": status_counts,
    }


@router.get("/billing", response_model=List[billing_schemas.SaaSBillingPortfolioItem])
async def read_billing_portfolio(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(PermissionChecker("manage_saas")),
) -> list[billing_schemas.SaaSBillingPortfolioItem]:
    """Return the tenant billing portfolio for manual SaaS operations."""

    companies = (
        await db.execute(select(Company).order_by(Company.name.asc(), Company.id.asc()))
    ).scalars().all()
    records = (
        await db.execute(
            select(SaaSBillingRecord).order_by(
                SaaSBillingRecord.created_at.desc(), SaaSBillingRecord.id.desc()
            )
        )
    ).scalars().all()
    latest_by_company: dict[uuid.UUID, SaaSBillingRecord] = {}
    for record in records:
        latest_by_company.setdefault(record.company_id, record)

    return [
        billing_schemas.SaaSBillingPortfolioItem(
            company_id=company.id,
            company_name=company.name,
            plan=company.plan,
            subscription_status=company.subscription_status,
            valid_until=company.valid_until,
            is_active=bool(company.is_active),
            billing_state=_billing_state(
                valid_until=company.valid_until,
                latest_record=latest_by_company.get(company.id),
            ),
            latest_record=(
                billing_schemas.SaaSBillingRecordOut.model_validate(latest_by_company[company.id])
                if company.id in latest_by_company
                else None
            ),
        )
        for company in companies
    ]


@router.get(
    "/companies/{company_id}/billing",
    response_model=List[billing_schemas.SaaSBillingRecordOut],
)
async def read_company_billing_records(
    company_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(PermissionChecker("manage_saas")),
) -> list[billing_schemas.SaaSBillingRecordOut]:
    """List all manual billing records for one tenant."""

    company = await db.scalar(select(Company).where(Company.id == company_id))
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    result = await db.execute(
        select(SaaSBillingRecord)
        .where(SaaSBillingRecord.company_id == company_id)
        .order_by(SaaSBillingRecord.period_end.desc(), SaaSBillingRecord.created_at.desc())
    )
    return [billing_schemas.SaaSBillingRecordOut.model_validate(record) for record in result.scalars().all()]


@router.post(
    "/companies/{company_id}/billing",
    response_model=billing_schemas.SaaSBillingRecordOut,
    status_code=201,
)
async def create_company_billing_record(
    company_id: uuid.UUID,
    billing_in: billing_schemas.SaaSBillingRecordCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(PermissionChecker("manage_saas")),
) -> billing_schemas.SaaSBillingRecordOut:
    """Register a pending manual SaaS charge awaiting verification."""

    company = await db.scalar(select(Company).where(Company.id == company_id))
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    plan = await _resolve_active_plan(db, billing_in.plan_code)

    if billing_in.reference:
        duplicate = await db.scalar(
            select(SaaSBillingRecord).where(
                SaaSBillingRecord.company_id == company_id,
                SaaSBillingRecord.reference == billing_in.reference.strip(),
            )
        )
        if duplicate:
            raise HTTPException(status_code=409, detail="Ya existe un cobro con esa referencia para la empresa")

    record_data = billing_in.model_dump()
    record_data.update(
        {
            "plan_code": plan.code,
            "currency": (billing_in.currency or plan.currency or "USD").upper(),
            "reference": billing_in.reference.strip() if billing_in.reference else None,
            "status": "PENDING",
            "company_id": company_id,
            "created_by_id": current_user.id,
            "updated_by_id": current_user.id,
        }
    )
    record = SaaSBillingRecord(**record_data)
    db.add(record)
    await db.flush()
    await log_activity(
        db,
        action="SAAS_BILLING_CREATED",
        entity_type="SaaSBillingRecord",
        entity_id=record.id,
        user_id=current_user.id,
        company_id=company_id,
        details={
            "status": record.status,
            "plan_code": record.plan_code,
            "period_start": record.period_start.isoformat(),
            "period_end": record.period_end.isoformat(),
            "amount": record.amount,
            "currency": record.currency,
            "reference": record.reference,
        },
    )
    await db.commit()
    await db.refresh(record)
    return billing_schemas.SaaSBillingRecordOut.model_validate(record)


@router.post(
    "/billing/{record_id}/verify",
    response_model=billing_schemas.SaaSBillingRecordOut,
)
async def verify_billing_record(
    record_id: uuid.UUID,
    verification: billing_schemas.SaaSBillingVerification,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(PermissionChecker("manage_saas")),
) -> billing_schemas.SaaSBillingRecordOut:
    """Approve/reject a manual payment and renew the tenant atomically."""

    record = await db.scalar(
        select(SaaSBillingRecord)
        .where(SaaSBillingRecord.id == record_id)
        .with_for_update()
    )
    if not record:
        raise HTTPException(status_code=404, detail="Billing record not found")
    company = await db.scalar(select(Company).where(Company.id == record.company_id).with_for_update())
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    was_paid = record.status == "PAID"
    if was_paid and verification.status != "PAID":
        raise HTTPException(status_code=409, detail="Un cobro aprobado no puede cambiarse desde este flujo")

    before_record = {
        "status": record.status,
        "reference": record.reference,
        "proof_url": record.proof_url,
        "rejection_reason": record.rejection_reason,
        "paid_at": record.paid_at.isoformat() if record.paid_at else None,
    }
    if verification.reference is not None:
        reference = verification.reference.strip()
        if reference and reference != record.reference:
            duplicate = await db.scalar(
                select(SaaSBillingRecord).where(
                    SaaSBillingRecord.company_id == record.company_id,
                    SaaSBillingRecord.reference == reference,
                    SaaSBillingRecord.id != record.id,
                )
            )
            if duplicate:
                raise HTTPException(status_code=409, detail="La referencia ya está usada por otro cobro")
        record.reference = reference or None
    if verification.proof_url is not None:
        record.proof_url = verification.proof_url.strip() or None
    if verification.notes is not None:
        record.notes = verification.notes.strip() or None

    now = datetime.now(timezone.utc)
    if verification.status == "PAID":
        if not record.reference and not record.proof_url:
            raise HTTPException(
                status_code=422,
                detail="Para aprobar el cobro debes indicar una referencia o comprobante",
            )
        record.status = "PAID"
        record.rejection_reason = None
        record.paid_at = record.paid_at or now
        record.verified_by_user_id = current_user.id
        record.verified_at = now
        record.updated_by_id = current_user.id

        company_before = {
            "plan": company.plan,
            "subscription_status": company.subscription_status,
            "valid_until": company.valid_until,
            "is_active": company.is_active,
        }
        period_end = record.period_end
        if period_end.tzinfo is None:
            period_end = period_end.replace(tzinfo=timezone.utc)
        current_expiry = _parse_subscription_expiry(company.valid_until)
        if period_end >= now:
            company.plan = record.plan_code
            company.subscription_status = "ACTIVE"
            company.is_active = True
            effective_expiry = max(current_expiry or now, period_end)
            company.valid_until = effective_expiry.isoformat()
        company_after = {
            "plan": company.plan,
            "subscription_status": company.subscription_status,
            "valid_until": company.valid_until,
            "is_active": company.is_active,
        }
        if not was_paid:
            await log_activity(
                db,
                action="SAAS_SUBSCRIPTION_RENEWED",
                entity_type="Company",
                entity_id=company.id,
                user_id=current_user.id,
                company_id=company.id,
                details={"billing_record_id": str(record.id), "before": company_before, "after": company_after},
            )
    else:
        if verification.status == "REJECTED" and len((verification.rejection_reason or "").strip()) < 3:
            raise HTTPException(status_code=422, detail="Indica por qué se rechazó el comprobante")
        record.status = verification.status
        record.rejection_reason = (
            verification.rejection_reason.strip()
            if verification.rejection_reason
            else None
        )
        record.updated_by_id = current_user.id
        record.verified_by_user_id = current_user.id
        record.verified_at = now

    after_record = {
        "status": record.status,
        "reference": record.reference,
        "proof_url": record.proof_url,
        "rejection_reason": record.rejection_reason,
        "paid_at": record.paid_at.isoformat() if record.paid_at else None,
    }
    await log_activity(
        db,
        action=(
            "SAAS_BILLING_VERIFIED"
            if verification.status == "PAID" and not was_paid
            else "SAAS_BILLING_REVIEWED"
        ),
        entity_type="SaaSBillingRecord",
        entity_id=record.id,
        user_id=current_user.id,
        company_id=company.id,
        details={"before": before_record, "after": after_record},
    )
    db.add(record)
    db.add(company)
    await db.commit()
    await db.refresh(record)
    return billing_schemas.SaaSBillingRecordOut.model_validate(record)

@router.get("/companies", response_model=List[schemas.Company])
async def read_companies(
    db: AsyncSession = Depends(get_db),
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(PermissionChecker("manage_saas")), # Need to ensure this permission exists or use is_superuser check
) -> Any:
    """
    Retrieve all companies (Super Admin only).
    """
    query = select(Company).offset(skip).limit(limit)
    result = await db.execute(query)
    return result.scalars().all()

@router.post("/companies", response_model=schemas.CompanyOnboardResponse)
async def create_company(
    *,
    db: AsyncSession = Depends(get_db),
    company_in: schemas.CompanyOnboard,
    current_user: User = Depends(PermissionChecker("manage_saas")),
) -> Any:
    """
    Register a new company (Tenant) with full onboarding:
    Creates Company + Default Branch + Admin Role + First Admin User.
    """
    # 1. Check if admin email already exists
    existing_user = await db.execute(select(User).where(User.email == company_in.admin_email))
    if existing_user.scalars().first():
        raise HTTPException(status_code=400, detail=f"El email {company_in.admin_email} ya está registrado")

    plan = await _resolve_active_plan(db, company_in.plan)
    valid_until = company_in.valid_until
    if not valid_until and plan.duration_days:
        valid_until = (datetime.utcnow() + timedelta(days=plan.duration_days)).isoformat()

    # 2. Create Company
    company = Company(
        name=company_in.name,
        tax_id=company_in.tax_id,
        address=company_in.address,
        email=company_in.email,
        phone=company_in.phone,
        plan=plan.code,
        valid_until=valid_until,
        is_active=True
    )
    db.add(company)
    await db.flush()  # Get company.id without committing

    # 3. Create Default Branch
    branch = Branch(
        name="Sede Principal",
        code="MAIN",
        address=company_in.address,
        phone=company_in.phone,
        email=company_in.email,
        is_warehouse=True,
        allow_pos=True,
        company_id=company.id
    )
    db.add(branch)
    await db.flush()

    # Operational modules resolve a default warehouse for every branch.  Keep
    # onboarding aligned with branch creation so a brand-new tenant can use
    # inventory, purchases, sales and ecommerce immediately.
    db.add(Warehouse(
        branch_id=branch.id,
        name="Bodega principal",
        code="PRINCIPAL",
        is_default=True,
        allows_ecommerce=True,
        company_id=company.id,
    ))

    # 4. Create Admin Role for this company
    admin_role = Role(
        name="Administrador",
        description="Administrador con acceso total a la empresa",
        permissions={"all": True},
        company_id=company.id
    )
    db.add(admin_role)
    await db.flush()  # Get admin_role.id

    # 5. Create First Admin User
    admin_user = User(
        email=company_in.admin_email,
        hashed_password=get_password_hash(company_in.admin_password),
        full_name=company_in.admin_name,
        is_superuser=False,
        role_id=admin_role.id,
        company_id=company.id
    )
    db.add(admin_user)

    # 6. Commit everything in one transaction
    await db.commit()
    await db.refresh(company)

    return schemas.CompanyOnboardResponse(
        company=schemas.Company.model_validate(company),
        admin_email=company_in.admin_email,
        branch_name="Sede Principal",
        message=f"Empresa '{company.name}' creada exitosamente con sucursal, rol y usuario administrador."
    )

@router.put("/companies/{id}", response_model=schemas.Company)
async def update_company(
    *,
    db: AsyncSession = Depends(get_db),
    id: uuid.UUID,
    company_in: schemas.CompanyAdminUpdate,
    current_user: User = Depends(PermissionChecker("manage_saas")),
) -> Any:
    """
    Update company details (including plan/status).
    """
    result = await db.execute(select(Company).where(Company.id == id))
    company = result.scalars().first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    update_data = company_in.model_dump(exclude_unset=True)
    if company_in.plan:
        plan = await _resolve_active_plan(db, company_in.plan)
        update_data["plan"] = plan.code

    before = {field: getattr(company, field) for field in update_data}
    for field, value in update_data.items():
        setattr(company, field, value)

    after = {field: getattr(company, field) for field in update_data}
    if before != after:
        await log_activity(
            db,
            action="SAAS_COMPANY_UPDATED",
            entity_type="Company",
            entity_id=company.id,
            user_id=current_user.id,
            company_id=company.id,
            details={"before": before, "after": after},
        )
    db.add(company)
    await db.commit()
    await db.refresh(company)
    return company
