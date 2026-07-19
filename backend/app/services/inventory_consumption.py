"""Inventory consumption rules shared by sales and fulfillment endpoints."""

import uuid

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.inventory_lot import InventoryLot
from app.models.product import Product


async def consume_fifo_lots(
    db: AsyncSession,
    *,
    product: Product,
    branch_id: uuid.UUID,
    company_id: uuid.UUID,
    quantity: float,
) -> float | None:
    """Consume traceable stock by expiry date and receipt age, returning its unit cost.

    Non-traceable products use the branch weighted-average cost, so this helper only
    acts on LOT and SERIAL products. Serial rows are quantity-one lots and naturally
    follow the same FEFO/FIFO ordering.
    """
    tracking_type = (product.tracking_type or "NONE").upper()
    if tracking_type == "NONE":
        return None

    lots_result = await db.execute(
        select(InventoryLot)
        .where(
            InventoryLot.product_id == product.id,
            InventoryLot.branch_id == branch_id,
            InventoryLot.company_id == company_id,
            InventoryLot.quantity > 0,
        )
        .order_by(InventoryLot.expiry_date.asc().nullslast(), InventoryLot.created_at.asc())
        .with_for_update()
    )
    lots = lots_result.scalars().all()
    remaining = quantity
    consumed_value = 0.0

    for lot in lots:
        if remaining <= 0:
            break
        used_quantity = min(lot.quantity, remaining)
        lot.quantity -= used_quantity
        remaining -= used_quantity
        consumed_value += used_quantity * lot.unit_cost

    if remaining > 0.000001:
        raise HTTPException(
            status_code=400,
            detail=f"El stock trazable de '{product.name}' no alcanza para despachar {quantity:g} unidad(es)",
        )
    return consumed_value / quantity if quantity else 0.0
