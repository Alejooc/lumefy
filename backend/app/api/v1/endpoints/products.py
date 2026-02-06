from typing import Any, List
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
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

@router.delete("/{product_id}", response_model=schemas.Product)
async def delete_product(
    *,
    db: AsyncSession = Depends(get_db),
    product_id: str,
    current_user: User = Depends(auth.get_current_user),
) -> Any:
    """
    Delete a product.
    """
    result = await db.execute(select(Product).where(Product.id == product_id))
    product = result.scalars().first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
        
    await db.delete(product)
    await db.commit()
    return product

@router.post("/import", response_model=dict)
async def import_products(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(auth.get_current_user),
) -> Any:
    """
    Import products from CSV or Excel file.
    Expected columns: name, sku, price, cost, stock, category_name
    """
    import pandas as pd
    import io
    from app.models.category import Category

    try:
        content = await file.read()
        if file.filename.endswith('.csv'):
            df = pd.read_csv(io.BytesIO(content))
        elif file.filename.endswith(('.xls', '.xlsx')):
            df = pd.read_excel(io.BytesIO(content))
        else:
            raise HTTPException(status_code=400, detail="Invalid file format")
            
        success_count = 0
        errors = []
        
        # Cache categories to avoid repeated DB lookups
        result = await db.execute(select(Category).where(Category.company_id == current_user.company_id))
        categories = result.scalars().all()
        category_map = {c.name.lower(): c.id for c in categories}
        
        for index, row in df.iterrows():
            try:
                # Basic validation
                if pd.isna(row.get('name')):
                    continue
                    
                category_name = str(row.get('category_name', '')).strip()
                category_id = None
                
                if category_name:
                    cat_key = category_name.lower()
                    if cat_key in category_map:
                        category_id = category_map[cat_key]
                    else:
                        # Create new category if it doesn't exist
                        new_category = Category(
                            name=category_name,
                            company_id=current_user.company_id
                        )
                        db.add(new_category)
                        await db.flush() # Get ID without committing
                        await db.refresh(new_category)
                        category_map[cat_key] = new_category.id
                        category_id = new_category.id
                
                product = Product(
                    name=row['name'],
                    sku=row.get('sku', None),
                    barcode=row.get('barcode', None),
                    price=float(row.get('price', 0)),
                    cost=float(row.get('cost', 0)),
                    min_stock=int(row.get('min_stock', 0)),
                    check_inventory=bool(row.get('check_inventory', True)),
                    category_id=category_id,
                    company_id=current_user.company_id
                )
                db.add(product)
                success_count += 1
                
            except Exception as e:
                errors.append(f"Row {index + 2}: {str(e)}")
                
        await db.commit()
        return {"success": True, "count": success_count, "errors": errors}
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Import failed: {str(e)}")
