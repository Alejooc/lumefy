from uuid import UUID
from pydantic import BaseModel, Field
class LocationIn(BaseModel):
 branch_id:UUID; name:str=Field(min_length=2,max_length=100); code:str=Field(min_length=1,max_length=40); location_type:str='STORAGE'; is_dispatch_location:bool=False
class LocationOut(LocationIn):
 id:UUID
 class Config: from_attributes=True
