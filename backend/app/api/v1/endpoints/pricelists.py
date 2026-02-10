from typing import Any, List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from app.api import deps
from app.api.deps import get_db, PermissionChecker
from app.models.user import User
from app.models.pricelist import PriceList
from app.models.pricelist_item import PriceListItem
from app.schemas import pricelist as schemas
from app.core.audit import log_activity

router = APIRouter()

@router.get("/", response_model=List[schemas.PriceList])
async def read_pricelists(
    skip: int = 0,
    limit: int = 100,
    type: str = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(PermissionChecker("manage_inventory")),
) -> Any:
    """
    Retrieve price lists.
    """
    query = select(PriceList).options(selectinload(PriceList.items))
    if type:
        query = query.where(PriceList.type == type)
    
    query = query.offset(skip).limit(limit)
    result = await db.execute(query)
    return result.scalars().all()

@router.post("/", response_model=schemas.PriceList)
async def create_pricelist(
    *,
    db: AsyncSession = Depends(get_db),
    pricelist_in: schemas.PriceListCreate,
    current_user: User = Depends(PermissionChecker("manage_inventory")),
) -> Any:
    """
    Create new price list.
    """
    pricelist = PriceList(
        name=pricelist_in.name,
        type=pricelist_in.type,
        currency=pricelist_in.currency,
        active=pricelist_in.active
    )
    db.add(pricelist)
    await db.flush()

    for item_in in pricelist_in.items:
        item = PriceListItem(
            pricelist_id=pricelist.id,
            product_id=item_in.product_id,
            min_quantity=item_in.min_quantity,
            price=item_in.price
        )
        db.add(item)
    
    await db.commit()
    await db.refresh(pricelist)
    
    # Reload with items
    query = select(PriceList).where(PriceList.id == pricelist.id).options(selectinload(PriceList.items))
    result = await db.execute(query)
    pricelist = result.scalars().first()
    
    await log_activity(db, "CREATE", "PriceList", pricelist.id, current_user.id, current_user.company_id)
    return pricelist

@router.get("/{id}", response_model=schemas.PriceList)
async def read_pricelist(
    id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(PermissionChecker("manage_inventory")),
) -> Any:
    """
    Get price list by ID.
    """
    query = select(PriceList).where(PriceList.id == id).options(selectinload(PriceList.items))
    result = await db.execute(query)
    pricelist = result.scalars().first()
    if not pricelist:
        raise HTTPException(status_code=404, detail="Price list not found")
    return pricelist

@router.put("/{id}", response_model=schemas.PriceList)
async def update_pricelist(
    *,
    db: AsyncSession = Depends(get_db),
    id: str,
    pricelist_in: schemas.PriceListUpdate,
    current_user: User = Depends(PermissionChecker("manage_inventory")),
) -> Any:
    """
    Update a price list.
    """
    query = select(PriceList).where(PriceList.id == id)
    result = await db.execute(query)
    pricelist = result.scalars().first()
    if not pricelist:
        raise HTTPException(status_code=404, detail="Price list not found")
    
    update_data = pricelist_in.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(pricelist, field, value)
    
    await db.commit()
    await db.refresh(pricelist)
    await log_activity(db, "UPDATE", "PriceList", pricelist.id, current_user.id, current_user.company_id)
    return pricelist

@router.post("/{id}/items", response_model=schemas.PriceListItem)
async def add_pricelist_item(
    *,
    db: AsyncSession = Depends(get_db),
    id: str,
    item_in: schemas.PriceListItemCreate,
    current_user: User = Depends(PermissionChecker("manage_inventory")),
) -> Any:
    """
    Add item to price list.
    """
    # Check if price list exists
    query = select(PriceList).where(PriceList.id == id)
    result = await db.execute(query)
    if not result.scalars().first():
        raise HTTPException(status_code=404, detail="Price list not found")

    item = PriceListItem(
        pricelist_id=id,
        **item_in.dict()
    )
    db.add(item)
    await db.commit()
    await db.refresh(item)
    return item
