from typing import List
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.core.database import get_db
from app.core.permissions import PermissionChecker
from app.models.user import User
from app.models.product import Product
from app.models.inventory import Inventory
from app.models.inventory_movement import InventoryMovement, MovementType
from app.models.manufacturing import BillOfMaterials, BillOfMaterialsLine, ManufacturingOrder, ManufacturingStatus
from app.schemas import manufacturing as schemas

router = APIRouter()

@router.get('/boms', response_model=List[schemas.BomOut])
async def list_boms(db: AsyncSession=Depends(get_db), current_user: User=Depends(PermissionChecker('manage_inventory'))):
    result = await db.execute(select(BillOfMaterials).options(selectinload(BillOfMaterials.lines)).where(BillOfMaterials.company_id==current_user.company_id, BillOfMaterials.is_active==True))
    return result.scalars().all()

@router.post('/boms', response_model=schemas.BomOut)
async def create_bom(data: schemas.BomIn, db: AsyncSession=Depends(get_db), current_user: User=Depends(PermissionChecker('manage_inventory'))):
    ids = {data.product_id, *(line.component_id for line in data.lines)}
    products = (await db.execute(select(Product.id).where(Product.id.in_(ids), Product.company_id==current_user.company_id))).scalars().all()
    if len(products) != len(ids) or not data.lines: raise HTTPException(400, 'Producto o componente inválido')
    bom = BillOfMaterials(product_id=data.product_id, quantity=data.quantity, company_id=current_user.company_id, created_by_id=current_user.id)
    db.add(bom); await db.flush()
    for line in data.lines: db.add(BillOfMaterialsLine(bom_id=bom.id, component_id=line.component_id, quantity=line.quantity, company_id=current_user.company_id))
    await db.commit(); await db.refresh(bom, attribute_names=['lines']); return bom

@router.get('/orders', response_model=List[schemas.ManufacturingOrderOut])
async def list_orders(db: AsyncSession=Depends(get_db), current_user: User=Depends(PermissionChecker('manage_inventory'))):
    return (await db.execute(select(ManufacturingOrder).where(ManufacturingOrder.company_id==current_user.company_id).order_by(ManufacturingOrder.created_at.desc()))).scalars().all()

@router.post('/orders', response_model=schemas.ManufacturingOrderOut)
async def create_order(data: schemas.ManufacturingOrderIn, db: AsyncSession=Depends(get_db), current_user: User=Depends(PermissionChecker('manage_inventory'))):
    bom = await db.scalar(select(BillOfMaterials).where(BillOfMaterials.id==data.bom_id, BillOfMaterials.company_id==current_user.company_id))
    if not bom: raise HTTPException(404, 'Lista de materiales no encontrada')
    order=ManufacturingOrder(**data.model_dump(), company_id=current_user.company_id, created_by_id=current_user.id); db.add(order); await db.commit(); await db.refresh(order); return order

async def _requirements(order: ManufacturingOrder) -> dict:
    factor = order.quantity / order.bom.quantity
    requirements = {}
    for line in order.bom.lines:
        requirements[line.component_id] = requirements.get(line.component_id, 0.0) + line.quantity * factor
    return requirements

@router.post('/orders/{order_id}/confirm', response_model=schemas.ManufacturingOrderOut)
async def confirm_order(order_id: UUID, db: AsyncSession=Depends(get_db), current_user: User=Depends(PermissionChecker('manage_inventory'))):
    order = await db.scalar(select(ManufacturingOrder).options(selectinload(ManufacturingOrder.bom).selectinload(BillOfMaterials.lines)).where(ManufacturingOrder.id==order_id, ManufacturingOrder.company_id==current_user.company_id))
    if not order or order.status != ManufacturingStatus.DRAFT: raise HTTPException(400, 'Orden no disponible para confirmar')
    requirements = await _requirements(order); inventories = {}
    for component_id, required in requirements.items():
        inventory = await db.scalar(select(Inventory).where(Inventory.product_id==component_id, Inventory.branch_id==order.branch_id).with_for_update())
        if not inventory or inventory.quantity - inventory.reserved_quantity < required: raise HTTPException(400, 'Stock insuficiente de componente')
        inventories[component_id] = inventory
    for component_id, required in requirements.items(): inventories[component_id].reserved_quantity += required
    order.status = ManufacturingStatus.CONFIRMED; await db.commit(); await db.refresh(order); return order

@router.post('/orders/{order_id}/complete', response_model=schemas.ManufacturingOrderOut)
async def complete_order(order_id: UUID, db: AsyncSession=Depends(get_db), current_user: User=Depends(PermissionChecker('manage_inventory'))):
    order = await db.scalar(select(ManufacturingOrder).options(selectinload(ManufacturingOrder.bom).selectinload(BillOfMaterials.lines)).where(ManufacturingOrder.id==order_id, ManufacturingOrder.company_id==current_user.company_id))
    if not order or order.status != ManufacturingStatus.CONFIRMED: raise HTTPException(400, 'Confirma la orden antes de completarla')
    production_cost = 0.0
    for component_id, need in (await _requirements(order)).items():
        inv=await db.scalar(select(Inventory).where(Inventory.product_id==component_id, Inventory.branch_id==order.branch_id).with_for_update())
        if not inv or inv.quantity < need or inv.reserved_quantity < need: raise HTTPException(400, 'La reserva de componentes no está disponible')
        previous=inv.quantity; inv.quantity-=need; inv.reserved_quantity-=need; production_cost += need * inv.average_cost
        db.add(InventoryMovement(product_id=component_id, branch_id=order.branch_id, user_id=current_user.id, type=MovementType.OUT, quantity=-need, previous_stock=previous, new_stock=inv.quantity, reference_id=str(order.id), reason='Manufacturing consumption', unit_cost=inv.average_cost, company_id=current_user.company_id))
    finished=await db.scalar(select(Inventory).where(Inventory.product_id==order.bom.product_id, Inventory.branch_id==order.branch_id).with_for_update())
    if not finished:
        finished=Inventory(product_id=order.bom.product_id, branch_id=order.branch_id, quantity=0, company_id=current_user.company_id); db.add(finished)
    previous=finished.quantity; unit_cost=production_cost/order.quantity; finished.quantity+=order.quantity
    finished.average_cost=((previous*finished.average_cost)+(order.quantity*unit_cost))/finished.quantity
    db.add(InventoryMovement(product_id=order.bom.product_id, branch_id=order.branch_id, user_id=current_user.id, type=MovementType.IN, quantity=order.quantity, previous_stock=previous, new_stock=finished.quantity, reference_id=str(order.id), reason='Manufacturing finished', unit_cost=unit_cost, company_id=current_user.company_id))
    order.status=ManufacturingStatus.DONE; await db.commit(); await db.refresh(order); return order

@router.post('/orders/{order_id}/cancel', response_model=schemas.ManufacturingOrderOut)
async def cancel_order(order_id: UUID, db: AsyncSession=Depends(get_db), current_user: User=Depends(PermissionChecker('manage_inventory'))):
    order = await db.scalar(select(ManufacturingOrder).options(selectinload(ManufacturingOrder.bom).selectinload(BillOfMaterials.lines)).where(ManufacturingOrder.id==order_id, ManufacturingOrder.company_id==current_user.company_id))
    if not order or order.status not in {ManufacturingStatus.DRAFT, ManufacturingStatus.CONFIRMED}: raise HTTPException(400, 'Orden no disponible para cancelar')
    if order.status == ManufacturingStatus.CONFIRMED:
        for component_id, need in (await _requirements(order)).items():
            inv=await db.scalar(select(Inventory).where(Inventory.product_id==component_id, Inventory.branch_id==order.branch_id).with_for_update())
            if not inv or inv.reserved_quantity < need: raise HTTPException(400, 'La reserva no puede liberarse')
            inv.reserved_quantity -= need
    order.status=ManufacturingStatus.CANCELLED; await db.commit(); await db.refresh(order); return order
