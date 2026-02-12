from typing import Any, List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.core.database import get_db
from app.models.company import Company
from app.models.user import User
from app.models.branch import Branch
from app.models.role import Role
from app.models.system_setting import SystemSetting
from app.schemas import system_setting as setting_schemas
from app.schemas import company as schemas
from app.core.permissions import PermissionChecker
from app.core.security import get_password_hash
import uuid

# This router should be protected. 
# For now we use a permission 'manage_saas' which superusers should have by default.
# Or we can check current_user.is_superuser

router = APIRouter()

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
    # Total Companies
    result = await db.execute(select(func.count(Company.id)))
    total_companies = result.scalar()
    
    # Active Companies
    result = await db.execute(select(func.count(Company.id)).where(Company.is_active == True))
    active_companies = result.scalar()
    
    # Total Users
    result = await db.execute(select(func.count(User.id)))
    total_users = result.scalar()
    
    # MRR Calculation (Estimated)
    # Get count by plan
    # Free: $0, Pro: $49, Enterprise: $199 (Example pricing)
    
    mrr = 0.0
    
    # Count Pro
    result = await db.execute(select(func.count(Company.id)).where(Company.plan == "PRO", Company.is_active == True))
    pro_count = result.scalar() or 0
    mrr += pro_count * 49.00
    
    # Count Enterprise
    result = await db.execute(select(func.count(Company.id)).where(Company.plan == "ENTERPRISE", Company.is_active == True))
    ent_count = result.scalar() or 0
    mrr += ent_count * 199.00
    
    return {
        "total_companies": total_companies,
        "active_companies": active_companies,
        "total_users": total_users,
        "mrr": mrr,
        "active_subscriptions": {
            "FREE": total_companies - pro_count - ent_count, # Approx
            "PRO": pro_count,
            "ENTERPRISE": ent_count
        }
    }

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

    # 2. Create Company
    company = Company(
        name=company_in.name,
        tax_id=company_in.tax_id,
        address=company_in.address,
        email=company_in.email,
        phone=company_in.phone,
        plan=company_in.plan or "FREE",
        valid_until=company_in.valid_until,
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
    company_in: schemas.CompanyUpdate,
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
    for field, value in update_data.items():
        setattr(company, field, value)
        
    db.add(company)
    await db.commit()
    await db.refresh(company)
    return company
