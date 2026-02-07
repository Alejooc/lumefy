from typing import Optional
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

# Properties to receive on creation
class CompanyCreate(CompanyBase):
    name: str

# Properties to receive on update
class CompanyUpdate(CompanyBase):
    pass

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
