from typing import Any, List
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.stock_take import StockTake, StockTakeItem, StockTakeStatus
from app.models.inventory import Inventory
from app.models.inventory_movement import InventoryMovement, MovementType
from app.models.product import Product
from app.models.user import User
from app.core.permissions import PermissionChecker
from app.schemas import stock_take as schemas

router = APIRouter()


@router.get("/", response_model=List[schemas.StockTakeSummary])
async def list_stock_takes(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(PermissionChecker("view_inventory")),
) -> Any:
    """List all stock takes for this company."""
    query = select(StockTake).options(
        selectinload(StockTake.branch)
    ).where(
        StockTake.company_id == current_user.company_id
    ).order_by(StockTake.created_at.desc())

    result = await db.execute(query)
    takes = result.scalars().all()

    # Add item_count manually
    summaries = []
    for take in takes:
        item_count_q = await db.execute(
            select(func.count(StockTakeItem.id)).where(StockTakeItem.stock_take_id == take.id)
        )
        count = item_count_q.scalar() or 0
        summary = schemas.StockTakeSummary(
            id=take.id,
            branch_id=take.branch_id,
            status=take.status,
            notes=take.notes,
            created_at=take.created_at,
            branch=take.branch,
            item_count=count
        )
        summaries.append(summary)

    return summaries


@router.post("/", response_model=schemas.StockTake)
async def create_stock_take(
    *,
    db: AsyncSession = Depends(get_db),
    stock_take_in: schemas.StockTakeCreate,
    current_user: User = Depends(PermissionChecker("manage_inventory")),
) -> Any:
    """
    Create a new stock take for a branch.
    Automatically loads all current inventory for that branch.
    """
    # Create the stock take header
    stock_take = StockTake(
        branch_id=stock_take_in.branch_id,
        user_id=current_user.id,
        company_id=current_user.company_id,
        status=StockTakeStatus.IN_PROGRESS,
        notes=stock_take_in.notes
    )
    db.add(stock_take)
    await db.flush()

    # Load all inventory for this branch
    inv_query = select(Inventory).where(
        Inventory.branch_id == stock_take_in.branch_id,
        Inventory.quantity > 0
    )
    inv_result = await db.execute(inv_query)
    inventories = inv_result.scalars().all()

    for inv in inventories:
        item = StockTakeItem(
            stock_take_id=stock_take.id,
            product_id=inv.product_id,
            system_qty=inv.quantity,
            counted_qty=None,
            difference=0.0,
            company_id=current_user.company_id,
        )
        db.add(item)

    await db.commit()

    # Reload with relationships
    return await _get_stock_take_detail(db, stock_take.id)


@router.get("/{stock_take_id}", response_model=schemas.StockTake)
async def get_stock_take(
    stock_take_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(PermissionChecker("view_inventory")),
) -> Any:
    """Get a stock take with all its items."""
    take = await _get_stock_take_detail(db, stock_take_id)
    if not take:
        raise HTTPException(status_code=404, detail="Stock take not found")
    return take


@router.put("/{stock_take_id}/count", response_model=schemas.StockTake)
async def update_counts(
    stock_take_id: UUID,
    *,
    db: AsyncSession = Depends(get_db),
    count_in: schemas.StockTakeCountUpdate,
    current_user: User = Depends(PermissionChecker("manage_inventory")),
) -> Any:
    """Update counted quantities for items in a stock take."""
    # Verify stock take exists and is in progress
    result = await db.execute(select(StockTake).where(StockTake.id == stock_take_id))
    stock_take = result.scalars().first()
    if not stock_take:
        raise HTTPException(status_code=404, detail="Stock take not found")
    if stock_take.status != StockTakeStatus.IN_PROGRESS:
        raise HTTPException(status_code=400, detail="Stock take is not in progress")

    for item_update in count_in.items:
        item_result = await db.execute(
            select(StockTakeItem).where(StockTakeItem.id == item_update.id)
        )
        item = item_result.scalars().first()
        if item:
            item.counted_qty = item_update.counted_qty
            item.difference = (item_update.counted_qty or 0) - item.system_qty

    await db.commit()
    return await _get_stock_take_detail(db, stock_take_id)


@router.post("/{stock_take_id}/apply", response_model=schemas.StockTake)
async def apply_stock_take(
    stock_take_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(PermissionChecker("manage_inventory")),
) -> Any:
    """
    Apply the stock take: generate ADJ movements for all items with differences.
    """
    result = await db.execute(select(StockTake).where(StockTake.id == stock_take_id))
    stock_take = result.scalars().first()
    if not stock_take:
        raise HTTPException(status_code=404, detail="Stock take not found")
    if stock_take.status != StockTakeStatus.IN_PROGRESS:
        raise HTTPException(status_code=400, detail="Stock take is not in progress")

    # Load items
    items_result = await db.execute(
        select(StockTakeItem).where(StockTakeItem.stock_take_id == stock_take_id)
    )
    items = items_result.scalars().all()

    for item in items:
        if item.counted_qty is None:
            continue  # Skip uncounted items
        if item.difference == 0:
            continue  # No adjustment needed

        # Get current inventory
        inv_result = await db.execute(
            select(Inventory).where(
                Inventory.product_id == item.product_id,
                Inventory.branch_id == stock_take.branch_id
            )
        )
        inv = inv_result.scalars().first()

        previous_stock = inv.quantity if inv else 0.0
        new_stock = item.counted_qty

        # Update inventory
        if inv:
            inv.quantity = new_stock
        else:
            inv = Inventory(
                product_id=item.product_id,
                branch_id=stock_take.branch_id,
                quantity=new_stock
            )
            db.add(inv)

        # Create ADJ movement
        movement = InventoryMovement(
            product_id=item.product_id,
            branch_id=stock_take.branch_id,
            user_id=current_user.id,
            type=MovementType.ADJ,
            quantity=item.difference,
            previous_stock=previous_stock,
            new_stock=new_stock,
            reason=f"Stock Take Adjustment (Take #{str(stock_take.id)[:8]})",
            reference_id=str(stock_take.id)
        )
        db.add(movement)

    # Mark as completed
    stock_take.status = StockTakeStatus.COMPLETED
    await db.commit()

    return await _get_stock_take_detail(db, stock_take_id)


@router.post("/{stock_take_id}/cancel", response_model=schemas.StockTake)
async def cancel_stock_take(
    stock_take_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(PermissionChecker("manage_inventory")),
) -> Any:
    """Cancel a stock take without applying changes."""
    result = await db.execute(select(StockTake).where(StockTake.id == stock_take_id))
    stock_take = result.scalars().first()
    if not stock_take:
        raise HTTPException(status_code=404, detail="Stock take not found")
    if stock_take.status != StockTakeStatus.IN_PROGRESS:
        raise HTTPException(status_code=400, detail="Stock take is not in progress")

    stock_take.status = StockTakeStatus.CANCELLED
    await db.commit()

    return await _get_stock_take_detail(db, stock_take_id)


async def _get_stock_take_detail(db: AsyncSession, stock_take_id: UUID):
    """Helper to load a stock take with all relationships."""
    query = select(StockTake).options(
        selectinload(StockTake.branch),
        selectinload(StockTake.items).selectinload(StockTakeItem.product).options(
            selectinload(Product.images),
            selectinload(Product.variants),
            selectinload(Product.brand),
            selectinload(Product.unit_of_measure),
            selectinload(Product.category)
        )
    ).where(StockTake.id == stock_take_id)

    result = await db.execute(query)
    return result.scalars().first()
