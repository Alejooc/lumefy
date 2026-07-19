from datetime import datetime
from uuid import UUID
from pydantic import BaseModel,Field
class CouponIn(BaseModel):
 storefront_id:UUID;code:str=Field(min_length=3,max_length=30);discount_type:str='PERCENT';value:float=Field(gt=0);minimum_amount:float=Field(default=0,ge=0);starts_at:datetime|None=None;ends_at:datetime|None=None;is_enabled:bool=True
class CouponOut(CouponIn):
 id:UUID
 class Config:from_attributes=True
