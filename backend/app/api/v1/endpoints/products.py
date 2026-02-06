from typing import Any, List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

# from app.api.v1 import deps
from app.core.database import get_db
from app.models.product import Product
from app.schemas import product as schemas
from app.models.user import User
from app.core import auth

router = APIRouter()

@router.get("/", response_model=List[schemas.Product])
async def read_products(
    db: AsyncSession = Depends(get_db),
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(auth.get_current_user),
) -> Any:
    """
    Retrieve products.
    """
    # Filter by company_id for multi-tenancy (assuming user has company_id)
    query = select(Product).offset(skip).limit(limit)
    if current_user.company_id:
        query = query.where(Product.company_id == current_user.company_id)
        
    result = await db.execute(query)
    products = result.scalars().all()
    return products

@router.post("/", response_model=schemas.Product)
async def create_product(
    *,
    db: AsyncSession = Depends(get_db),
    product_in: schemas.ProductCreate,
    current_user: User = Depends(auth.get_current_user),
) -> Any:
    """
    Create new product.
    """
    try:
        product = Product(**product_in.model_dump(), company_id=current_user.company_id)
        db.add(product)
        await db.commit()
        await db.refresh(product)
        return product
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/{product_id}", response_model=schemas.Product)
async def update_product(
    *,
    db: AsyncSession = Depends(get_db),
    product_id: str,
    product_in: schemas.ProductUpdate,
    current_user: User = Depends(auth.get_current_user),
) -> Any:
    """
    Update a product.
    """
    result = await db.execute(select(Product).where(Product.id == product_id))
    product = result.scalars().first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
        
    update_data = product_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(product, field, value)
        
    db.add(product)
    await db.commit()
    await db.refresh(product)
    return product
