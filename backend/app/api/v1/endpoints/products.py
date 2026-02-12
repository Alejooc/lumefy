from typing import Any, List
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.models.product import Product
from app.models.product_variant import ProductVariant
from app.schemas import product as schemas
from app.schemas import product_variant as variant_schemas
from app.models.user import User
from app.core.permissions import PermissionChecker
from app.core.audit import log_activity

router = APIRouter()

@router.get("/", response_model=List[schemas.Product])
async def read_products(
    db: AsyncSession = Depends(get_db),
    skip: int = 0,
    limit: int = 100,
    search: str = None,
    category_id: str = None,
    brand_id: str = None,
    product_type: str = None,
    current_user: User = Depends(PermissionChecker("view_products")),
) -> Any:
    """Retrieve products with all relations."""
    query = select(Product).options(
        selectinload(Product.brand),
        selectinload(Product.unit_of_measure),
        selectinload(Product.purchase_uom),
        selectinload(Product.variants),
        selectinload(Product.category)
    ).offset(skip).limit(limit)
    
    if current_user.company_id:
        query = query.where(Product.company_id == current_user.company_id)
        
    if search:
        search_filter = f"%{search}%"
        query = query.where(
            or_(
                Product.name.ilike(search_filter),
                Product.sku.ilike(search_filter),
                Product.barcode.ilike(search_filter),
                Product.internal_reference.ilike(search_filter)
            )
        )
    
    if category_id:
        query = query.where(Product.category_id == category_id)
    if brand_id:
        query = query.where(Product.brand_id == brand_id)
    if product_type:
        query = query.where(Product.product_type == product_type)
        
    result = await db.execute(query)
    return result.scalars().all()

@router.get("/{product_id}", response_model=schemas.Product)
async def read_product(
    product_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(PermissionChecker("view_products")),
) -> Any:
    """Get a single product with all relations."""
    result = await db.execute(
        select(Product).options(
            selectinload(Product.brand),
            selectinload(Product.unit_of_measure),
            selectinload(Product.purchase_uom),
            selectinload(Product.variants),
            selectinload(Product.category)
        ).where(
            Product.id == product_id,
            Product.company_id == current_user.company_id
        )
    )
    product = result.scalars().first()
    if not product:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    return product

@router.post("/", response_model=schemas.Product)
async def create_product(
    *,
    db: AsyncSession = Depends(get_db),
    product_in: schemas.ProductCreate,
    current_user: User = Depends(PermissionChecker("manage_inventory")),
) -> Any:
    """Create new product."""
    try:
        product = Product(**product_in.model_dump(), company_id=current_user.company_id)
        db.add(product)
        await db.commit()
        await db.refresh(product)
        
        await log_activity(db, action="CREATE", entity_type="Product", entity_id=product.id,
                           user_id=current_user.id, company_id=current_user.company_id,
                           details={"name": product_in.name, "sku": product_in.sku})
        
        # Reload with relations
        result = await db.execute(
            select(Product).options(
                selectinload(Product.brand),
                selectinload(Product.unit_of_measure),
                selectinload(Product.purchase_uom),
                selectinload(Product.variants)
            ).where(Product.id == product.id)
        )
        return result.scalars().first()
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/{product_id}", response_model=schemas.Product)
async def update_product(
    *,
    db: AsyncSession = Depends(get_db),
    product_id: str,
    product_in: schemas.ProductUpdate,
    current_user: User = Depends(PermissionChecker("manage_inventory")),
) -> Any:
    """Update a product."""
    result = await db.execute(
        select(Product).where(
            Product.id == product_id,
            Product.company_id == current_user.company_id
        )
    )
    product = result.scalars().first()
    if not product:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
        
    update_data = product_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(product, field, value)
        
    await db.commit()
    await db.refresh(product)
    
    await log_activity(db, action="UPDATE", entity_type="Product", entity_id=product.id,
                       user_id=current_user.id, company_id=current_user.company_id,
                       details=update_data)
    
    # Reload with relations
    result = await db.execute(
        select(Product).options(
            selectinload(Product.brand),
            selectinload(Product.unit_of_measure),
            selectinload(Product.purchase_uom),
            selectinload(Product.variants)
        ).where(Product.id == product.id)
    )
    return result.scalars().first()

@router.delete("/{product_id}")
async def delete_product(
    *,
    db: AsyncSession = Depends(get_db),
    product_id: str,
    current_user: User = Depends(PermissionChecker("manage_inventory")),
) -> Any:
    """Delete a product and its variants."""
    result = await db.execute(
        select(Product).options(
            selectinload(Product.variants)
        ).where(
            Product.id == product_id,
            Product.company_id == current_user.company_id
        )
    )
    product = result.scalars().first()
    if not product:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    
    # Delete variants first
    for variant in product.variants:
        await db.delete(variant)
    
    await db.delete(product)
    await db.commit()
    
    await log_activity(db, action="DELETE", entity_type="Product", entity_id=product_id,
                       user_id=current_user.id, company_id=current_user.company_id)
    return {"ok": True}

# --- Variant Sub-Endpoints ---

@router.post("/{product_id}/variants", response_model=variant_schemas.ProductVariant)
async def add_variant(
    *,
    db: AsyncSession = Depends(get_db),
    product_id: str,
    variant_in: variant_schemas.ProductVariantCreate,
    current_user: User = Depends(PermissionChecker("manage_inventory")),
) -> Any:
    """Add a variant to a product."""
    # Verify product exists and belongs to company
    result = await db.execute(
        select(Product).where(
            Product.id == product_id,
            Product.company_id == current_user.company_id
        )
    )
    if not result.scalars().first():
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    
    variant = ProductVariant(**variant_in.model_dump(), product_id=product_id)
    db.add(variant)
    await db.commit()
    await db.refresh(variant)
    return variant

@router.put("/{product_id}/variants/{variant_id}", response_model=variant_schemas.ProductVariant)
async def update_variant(
    *,
    db: AsyncSession = Depends(get_db),
    product_id: str,
    variant_id: str,
    variant_in: variant_schemas.ProductVariantUpdate,
    current_user: User = Depends(PermissionChecker("manage_inventory")),
) -> Any:
    """Update a product variant."""
    result = await db.execute(
        select(ProductVariant).where(
            ProductVariant.id == variant_id,
            ProductVariant.product_id == product_id
        )
    )
    variant = result.scalars().first()
    if not variant:
        raise HTTPException(status_code=404, detail="Variante no encontrada")
    
    update_data = variant_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(variant, field, value)
    
    await db.commit()
    await db.refresh(variant)
    return variant

@router.delete("/{product_id}/variants/{variant_id}")
async def delete_variant(
    *,
    db: AsyncSession = Depends(get_db),
    product_id: str,
    variant_id: str,
    current_user: User = Depends(PermissionChecker("manage_inventory")),
) -> Any:
    """Delete a product variant."""
    result = await db.execute(
        select(ProductVariant).where(
            ProductVariant.id == variant_id,
            ProductVariant.product_id == product_id
        )
    )
    variant = result.scalars().first()
    if not variant:
        raise HTTPException(status_code=404, detail="Variante no encontrada")
    
    await db.delete(variant)
    await db.commit()
    return {"ok": True}

# --- Import ---

@router.post("/import", response_model=dict)
async def import_products(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(PermissionChecker("manage_inventory")),
) -> Any:
    """Import products from CSV or Excel file."""
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
            raise HTTPException(status_code=400, detail="Formato de archivo inválido. Use CSV o Excel.")
            
        success_count = 0
        errors = []
        
        result = await db.execute(select(Category).where(Category.company_id == current_user.company_id))
        categories = result.scalars().all()
        category_map = {c.name.lower(): c.id for c in categories}
        
        for index, row in df.iterrows():
            try:
                if pd.isna(row.get('name')):
                    continue
                    
                category_name = str(row.get('category_name', '')).strip()
                category_id = None
                
                if category_name:
                    cat_key = category_name.lower()
                    if cat_key in category_map:
                        category_id = category_map[cat_key]
                    else:
                        new_category = Category(name=category_name, company_id=current_user.company_id)
                        db.add(new_category)
                        await db.flush()
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
                    track_inventory=bool(row.get('track_inventory', True)),
                    category_id=category_id,
                    company_id=current_user.company_id
                )
                db.add(product)
                success_count += 1
                
            except Exception as e:
                errors.append(f"Fila {index + 2}: {str(e)}")
                
        await db.commit()
        return {"success": True, "count": success_count, "errors": errors}
        
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Importación falló: {str(e)}")
