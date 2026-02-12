from typing import List, Optional
from pydantic import BaseModel
from uuid import UUID

# Package Type
class PackageTypeBase(BaseModel):
    name: str
    width: float
    height: float
    length: float
    max_weight: float

class PackageTypeCreate(PackageTypeBase):
    pass

class PackageType(PackageTypeBase):
    id: UUID
    
    class Config:
        from_attributes = True

# Sale Package
class SalePackageItemBase(BaseModel):
    sale_item_id: UUID
    quantity: float

class SalePackageItemCreate(SalePackageItemBase):
    pass

class SalePackageItem(SalePackageItemBase):
    package_id: UUID
    
    class Config:
        from_attributes = True

class SalePackageBase(BaseModel):
    sale_id: UUID
    package_type_id: Optional[UUID] = None
    tracking_number: Optional[str] = None
    weight: float = 0.0
    shipping_label_url: Optional[str] = None

class SalePackageCreate(SalePackageBase):
    items: List[SalePackageItemCreate] = []

class SalePackage(SalePackageBase):
    id: UUID
    items: List[SalePackageItem] = []
    package_type: Optional[PackageType] = None
    
    class Config:
        from_attributes = True

# Picking Update
class PickingUpdate(BaseModel):
    sale_item_id: UUID
    quantity_picked: float
