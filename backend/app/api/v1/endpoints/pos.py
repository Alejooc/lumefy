from typing import Any, List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.models.sale import Sale, SaleItem, SaleStatus, Payment
from app.models.product import Product
from app.models.inventory import Inventory
from app.models.inventory_movement import InventoryMovement, MovementType
from app.models.user import User
from app.models.category import Category
from app.core.permissions import PermissionChecker
from app.schemas import pos as schemas
import uuid
from datetime import datetime, timezone

router = APIRouter()

# Dependency to check if POS app is active for company
async def check_pos_app(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(PermissionChecker("create_sales")) # Use existing permission
):
    from app.models.company_app_install import CompanyAppInstall
    from app.models.app_definition import AppDefinition
    
    # Verify the user's company installed the POS App
    result = await db.execute(
        select(CompanyAppInstall).join(AppDefinition).where(
            CompanyAppInstall.company_id == current_user.company_id,
            AppDefinition.slug == "pos_module",
            CompanyAppInstall.is_enabled == True
        )
    )
    if not result.scalars().first():
        raise HTTPException(status_code=403, detail="POS Module is not installed for this company.")
    return current_user

@router.get("/products", response_model=List[schemas.POSProduct])
async def get_pos_products(
    branch_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(check_pos_app)
) -> Any:
    """
    Optimized endpoint to fetch all products and their stock for the POS interface.
    """
    query = select(Product, Inventory, Category).outerjoin(
        Inventory, 
        and_(Inventory.product_id == Product.id, Inventory.branch_id == branch_id)
    ).outerjoin(
        Category, Category.id == Product.category_id
    ).where(Product.company_id == current_user.company_id, Product.is_active == True)
    
    result = await db.execute(query)
    rows = result.all()
    
    products = []
    for product, inventory, category in rows:
        products.append({
            "id": product.id,
            "name": product.name,
            "sku": product.sku,
            "barcode": product.barcode,
            "price": product.price,
            "stock": inventory.quantity if inventory else 0.0,
            "category_id": product.category_id,
            "category_name": category.name if category else None,
            "image_url": product.image_url
        })
        
    return products

@router.post("/checkout", response_model=dict)
async def pos_checkout(
    *,
    db: AsyncSession = Depends(get_db),
    checkout_in: schemas.POSCheckout,
    current_user: User = Depends(check_pos_app)
) -> Any:
    """
    Fast checkout logic for POS:
    1. Creates Sale in COMPLETED status.
    2. Deducts Inventory instantly.
    3. Registers Payment.
    """
    try:
        # 1. Create Sale Header
        sale = Sale(
            branch_id=checkout_in.branch_id,
            user_id=current_user.id,
            client_id=checkout_in.client_id,
            status=SaleStatus.COMPLETED, # Instantly completed
            payment_method=checkout_in.payment_method,
            notes=checkout_in.notes or "Venta POS",
            subtotal=0.0,
            tax=0.0,
            discount=0.0,
            total=0.0,
            company_id=current_user.company_id,
            completed_at=datetime.now(timezone.utc),
            delivered_at=datetime.now(timezone.utc)
        )
        db.add(sale)
        await db.flush()
        
        total_amount = 0.0
        
        # 2. Process Items and Inventory
        for item_in in checkout_in.items:
            # Sale Item
            item_total = (item_in.price * item_in.quantity) - item_in.discount
            total_amount += item_total
            
            sale_item = SaleItem(
                sale_id=sale.id,
                product_id=item_in.product_id,
                quantity=item_in.quantity,
                quantity_picked=item_in.quantity, # Fully picked
                price=item_in.price,
                discount=item_in.discount,
                total=item_total
            )
            db.add(sale_item)
            
            # Inventory Deduction
            inv_result = await db.execute(
                select(Inventory).where(
                    Inventory.product_id == item_in.product_id,
                    Inventory.branch_id == checkout_in.branch_id
                )
            )
            inventory = inv_result.scalars().first()
            if not inventory:
                inventory = Inventory(
                    product_id=item_in.product_id,
                    branch_id=checkout_in.branch_id,
                    quantity=0.0
                )
                db.add(inventory)
            
            # Capture stock BEFORE deduction for the kardex
            prev_qty = inventory.quantity
            inventory.quantity -= item_in.quantity
            new_qty = inventory.quantity
            
            # Inventory Movement (kardex entry)
            movement = InventoryMovement(
                product_id=item_in.product_id,
                branch_id=checkout_in.branch_id,
                user_id=current_user.id,
                type=MovementType.OUT,
                quantity=-item_in.quantity,
                previous_stock=prev_qty,
                new_stock=new_qty,
                reference_id=str(sale.id),
                reason=f"Venta POS \u2014 {current_user.full_name or current_user.email}"
            )
            db.add(movement)
            
        # 3. Finalize Sale
        sale.subtotal = total_amount
        sale.total = total_amount
        
        # 4. Register Payment
        payment = Payment(
            sale_id=sale.id,
            method=checkout_in.payment_method,
            amount=checkout_in.amount_paid
        )
        db.add(payment)

        # 5. CRM: If CREDIT, register debt
        if sale.payment_method == "CREDIT" and sale.client_id:
            from app.models.client import Client
            from app.models.account_ledger import AccountLedger, LedgerType, PartnerType
            
            client_result = await db.execute(select(Client).where(Client.id == sale.client_id))
            client = client_result.scalar_one_or_none()
            if client:
                new_balance = client.current_balance + sale.total
                client.current_balance = new_balance
                db.add(client)
                
                ledger = AccountLedger(
                    partner_id=client.id,
                    partner_type=PartnerType.CLIENT,
                    type=LedgerType.CHARGE,
                    amount=sale.total,
                    balance_after=new_balance,
                    reference_id=str(sale.id),
                    description=f"Venta POS a crédito"
                )
                db.add(ledger)

        await db.commit()
        await db.refresh(sale)
        
        return {"success": True, "sale_id": sale.id, "total": sale.total, "change": checkout_in.amount_paid - sale.total}

    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=400, detail=str(e))
