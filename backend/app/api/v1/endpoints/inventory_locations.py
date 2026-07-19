from typing import List
from fastapi import APIRouter,Depends,HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.permissions import PermissionChecker
from app.models.branch import Branch
from app.models.inventory_location import InventoryLocation
from app.models.user import User
from app.schemas import inventory_location as schemas
router=APIRouter()
@router.get('/',response_model=List[schemas.LocationOut])
async def list_locations(branch_id:str|None=None,db:AsyncSession=Depends(get_db),current_user:User=Depends(PermissionChecker('view_inventory'))):
 query=select(InventoryLocation).join(Branch).where(Branch.company_id==current_user.company_id,InventoryLocation.is_active==True)
 if branch_id: query=query.where(InventoryLocation.branch_id==branch_id)
 return (await db.execute(query.order_by(InventoryLocation.code))).scalars().all()
@router.post('/',response_model=schemas.LocationOut)
async def create_location(data:schemas.LocationIn,db:AsyncSession=Depends(get_db),current_user:User=Depends(PermissionChecker('manage_inventory'))):
 branch=await db.scalar(select(Branch).where(Branch.id==data.branch_id,Branch.company_id==current_user.company_id))
 if not branch: raise HTTPException(404,'Sucursal no encontrada')
 if await db.scalar(select(InventoryLocation.id).where(InventoryLocation.branch_id==data.branch_id,InventoryLocation.code==data.code)): raise HTTPException(409,'El código de ubicación ya existe')
 item=InventoryLocation(**data.model_dump(),company_id=current_user.company_id,created_by_id=current_user.id);db.add(item);await db.commit();await db.refresh(item);return item
