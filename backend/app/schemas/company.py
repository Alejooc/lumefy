from typing import Optional, List
from uuid import UUID
from pydantic import BaseModel, ConfigDict

# Shared properties
class CompanyBase(BaseModel):
    name: Optional[str] = None
    tax_id: Optional[str] = None
    address: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    website: Optional[str] = None
    currency: Optional[str] = "USD"
    currency_symbol: Optional[str] = "$"
    logo_url: Optional[str] = None
    
    plan: Optional[str] = "FREE"
    valid_until: Optional[str] = None
    subscription_status: Optional[str] = "ACTIVE"
    is_active: Optional[bool] = True

# Properties to receive on creation
class CompanyCreate(CompanyBase):
    name: str

# Schema for onboarding a new company with its first admin user
class CompanyOnboard(CompanyCreate):
    admin_email: str
    admin_password: str
    admin_name: str = "Administrador"

# Properties to receive on update
class CompanyUpdate(BaseModel):
    """Fields a tenant administrator is allowed to change for its own company."""
    name: Optional[str] = None
    tax_id: Optional[str] = None
    address: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    website: Optional[str] = None
    currency: Optional[str] = None
    currency_symbol: Optional[str] = None
    logo_url: Optional[str] = None


class CompanyAdminUpdate(BaseModel):
    """Full company update, restricted to SaaS superadmins.

    Every field is optional with a ``None`` default.  Inheriting creation
    defaults here previously made a partial update silently reset a tenant to
    the FREE plan or reactivate it.
    """

    name: Optional[str] = None
    tax_id: Optional[str] = None
    address: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    website: Optional[str] = None
    currency: Optional[str] = None
    currency_symbol: Optional[str] = None
    logo_url: Optional[str] = None
    plan: Optional[str] = None
    valid_until: Optional[str] = None
    subscription_status: Optional[str] = None
    is_active: Optional[bool] = None

# Properties shared by models stored in DB
class CompanyInDBBase(CompanyBase):
    id: UUID
    
    model_config = ConfigDict(from_attributes=True)

# Properties to return to client
class Company(CompanyInDBBase):
    pass

# Properties stored in DB
class CompanyInDB(CompanyInDBBase):
    pass

# Response for onboarding
class CompanyOnboardResponse(BaseModel):
    company: Company
    admin_email: str
    branch_name: str
    message: str

    model_config = ConfigDict(from_attributes=True)

class CompanySubscriptionExtend(BaseModel):
    valid_until: str # ISO Date YYYY-MM-DD
    plan: Optional[str] = None # Optional upgrade
    subscription_status: Optional[str] = "ACTIVE"
