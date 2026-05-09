from typing import Any, List
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_
from sqlalchemy.orm import selectinload
import re

from app.core.database import get_db
from app.models.product import Product
from app.models.product_variant import ProductVariant
from app.models.storefront import PublishedProduct, Storefront
from app.schemas import product as schemas
from app.schemas import product_variant as variant_schemas
from app.models.user import User
from app.core.permissions import PermissionChecker
from app.core.plan_limits import PlanLimitChecker
from app.core.audit import log_activity

router = APIRouter()


def _slugify(value: str) -> str:
    value = (value or "").strip().lower()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    return value.strip("-") or "product"


async def _get_primary_storefront(db: AsyncSession, company_id: str | None) -> Storefront | None:
    if not company_id:
        return None
    result = await db.execute(
        select(Storefront).where(
            Storefront.company_id == company_id,
            Storefront.is_active == True
        ).order_by(Storefront.created_at.asc())
    )
    return result.scalars().first()


def _extract_ecommerce_payload(payload: dict[str, Any]) -> dict[str, Any]:
    keys = {
        "visible_in_ecommerce",
        "ecommerce_slug",
        "ecommerce_title",
        "ecommerce_description",
        "ecommerce_price_override",
        "ecommerce_compare_at_price",
        "ecommerce_is_featured",
        "ecommerce_show_stock",
        "ecommerce_seo_title",
        "ecommerce_seo_description",
    }
    return {key: payload.pop(key) for key in list(payload.keys()) if key in keys}


async def _sync_product_ecommerce(
    db: AsyncSession,
    *,
    product: Product,
    company_id: str | None,
    ecommerce_data: dict[str, Any],
) -> None:
    if not ecommerce_data:
        return

    storefront = await _get_primary_storefront(db, company_id)
    visible = bool(ecommerce_data.get("visible_in_ecommerce", False))

    result = await db.execute(
        select(PublishedProduct).where(
            PublishedProduct.product_id == product.id,
            PublishedProduct.company_id == company_id,
            PublishedProduct.is_active == True
        )
    )
    published_product = result.scalars().first()

    if not storefront:
        if visible:
            raise HTTPException(status_code=400, detail="Primero configura una tienda ecommerce para publicar productos.")
        return

    if not visible:
        if published_product:
            published_product.is_published = False
            published_product.updated_by_id = product.updated_by_id
            db.add(published_product)
        return

    slug = ecommerce_data.get("ecommerce_slug") or _slugify(product.name)
    if published_product:
        published_product.storefront_id = storefront.id
        published_product.custom_title = ecommerce_data.get("ecommerce_title") or None
        published_product.custom_description = ecommerce_data.get("ecommerce_description") or None
        published_product.slug = slug
        published_product.price_override = ecommerce_data.get("ecommerce_price_override")
        published_product.compare_at_price = ecommerce_data.get("ecommerce_compare_at_price")
        published_product.is_published = True
        published_product.is_featured = bool(ecommerce_data.get("ecommerce_is_featured", False))
        published_product.show_stock = bool(ecommerce_data.get("ecommerce_show_stock", True))
        published_product.seo_title = ecommerce_data.get("ecommerce_seo_title") or None
        published_product.seo_description = ecommerce_data.get("ecommerce_seo_description") or None
        published_product.updated_by_id = product.updated_by_id
        db.add(published_product)
        return

    db.add(
        PublishedProduct(
            storefront_id=storefront.id,
            product_id=product.id,
            custom_title=ecommerce_data.get("ecommerce_title") or None,
            custom_description=ecommerce_data.get("ecommerce_description") or None,
            slug=slug,
            price_override=ecommerce_data.get("ecommerce_price_override"),
            compare_at_price=ecommerce_data.get("ecommerce_compare_at_price"),
            is_published=True,
            is_featured=bool(ecommerce_data.get("ecommerce_is_featured", False)),
            show_stock=bool(ecommerce_data.get("ecommerce_show_stock", True)),
            seo_title=ecommerce_data.get("ecommerce_seo_title") or None,
            seo_description=ecommerce_data.get("ecommerce_seo_description") or None,
            company_id=company_id,
            created_by_id=product.created_by_id,
            updated_by_id=product.updated_by_id,
        )
    )


def _attach_ecommerce_state(product: Product, published_product: PublishedProduct | None) -> None:
    product.visible_in_ecommerce = bool(published_product and published_product.is_published)
    product.ecommerce_slug = published_product.slug if published_product else None
    product.ecommerce_title = published_product.custom_title if published_product else None
    product.ecommerce_description = published_product.custom_description if published_product else None
    product.ecommerce_price_override = published_product.price_override if published_product else None
    product.ecommerce_compare_at_price = published_product.compare_at_price if published_product else None
    product.ecommerce_is_featured = bool(published_product.is_featured) if published_product else False
    product.ecommerce_show_stock = bool(published_product.show_stock) if published_product else True
    product.ecommerce_seo_title = published_product.seo_title if published_product else None
    product.ecommerce_seo_description = published_product.seo_description if published_product else None

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
        selectinload(Product.images),
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
    products = result.scalars().all()
    if not products or not current_user.company_id:
        return products

    product_ids = [product.id for product in products]
    published_result = await db.execute(
        select(PublishedProduct).where(
            PublishedProduct.company_id == current_user.company_id,
            PublishedProduct.product_id.in_(product_ids),
            PublishedProduct.is_active == True
        )
    )
    published_map = {item.product_id: item for item in published_result.scalars().all()}
    for product in products:
        _attach_ecommerce_state(product, published_map.get(product.id))
    return products

@router.get("/export")
async def export_products(
    db: AsyncSession = Depends(get_db),
    format: str = "excel",
    search: str = None,
    category_id: str = None,
    brand_id: str = None,
    current_user: User = Depends(PermissionChecker("view_products")),
) -> Any:
    """Export products to Excel or CSV."""
    from app.services.export_service import ExportService

    query = select(Product).options(
        selectinload(Product.brand),
        selectinload(Product.category),
        selectinload(Product.unit_of_measure),
    )
    if current_user.company_id:
        query = query.where(Product.company_id == current_user.company_id)
    if search:
        search_filter = f"%{search}%"
        query = query.where(
            or_(Product.name.ilike(search_filter), Product.sku.ilike(search_filter))
        )
    if category_id:
        query = query.where(Product.category_id == category_id)
    if brand_id:
        query = query.where(Product.brand_id == brand_id)

    result = await db.execute(query)
    products = result.scalars().all()

    columns = {
        "sku": "SKU",
        "name": "Nombre",
        "product_type": "Tipo",
        "category_name": "Categoría",
        "brand_name": "Marca",
        "sale_price": "Precio Venta",
        "cost_price": "Precio Costo",
        "uom_name": "Unidad",
        "is_active": "Activo",
    }

    rows = []
    for p in products:
        rows.append({
            "sku": p.sku or "",
            "name": p.name,
            "product_type": p.product_type or "",
            "category_name": p.category.name if p.category else "",
            "brand_name": p.brand.name if p.brand else "",
            "sale_price": float(p.sale_price) if p.sale_price else 0,
            "cost_price": float(p.cost_price) if p.cost_price else 0,
            "uom_name": p.unit_of_measure.name if p.unit_of_measure else "",
            "is_active": "Sí" if p.is_active else "No",
        })

    if format == "csv":
        return ExportService.to_csv_response(rows, columns, filename="productos")
    return ExportService.to_excel_response(rows, columns, filename="productos")

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
            selectinload(Product.images),
            selectinload(Product.category)
        ).where(
            Product.id == product_id,
            Product.company_id == current_user.company_id
        )
    )
    product = result.scalars().first()
    if not product:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    published_result = await db.execute(
        select(PublishedProduct).where(
            PublishedProduct.product_id == product.id,
            PublishedProduct.company_id == current_user.company_id,
            PublishedProduct.is_active == True
        )
    )
    _attach_ecommerce_state(product, published_result.scalars().first())
    return product

@router.post("/", response_model=schemas.Product)
async def create_product(
    *,
    db: AsyncSession = Depends(get_db),
    product_in: schemas.ProductCreate,
    current_user: User = Depends(PermissionChecker("manage_inventory")),
    _plan: User = Depends(PlanLimitChecker(resource="products", count_model=Product)),
) -> Any:
    """Create new product."""
    try:
        # Extract images data
        images_data = product_in.images
        product_data = product_in.model_dump(exclude={"images"})
        ecommerce_data = _extract_ecommerce_payload(product_data)
        
        product = Product(**product_data, company_id=current_user.company_id, created_by_id=current_user.id, updated_by_id=current_user.id)
        db.add(product)
        await db.commit()
        await db.refresh(product)
        
        # Create images
        from app.models.product_image import ProductImage
        if images_data:
            for img in images_data:
                new_img = ProductImage(**img.model_dump(), product_id=product.id)
                db.add(new_img)
        await _sync_product_ecommerce(
            db,
            product=product,
            company_id=current_user.company_id,
            ecommerce_data=ecommerce_data,
        )
        await db.commit()
        
        await log_activity(db, action="CREATE", entity_type="Product", entity_id=product.id,
                           user_id=current_user.id, company_id=current_user.company_id,
                           details={"name": product_in.name, "sku": product_in.sku})
        
        # Reload with relations
        result = await db.execute(
            select(Product).options(
                selectinload(Product.brand),
                selectinload(Product.unit_of_measure),
                selectinload(Product.purchase_uom),
                selectinload(Product.variants),
                selectinload(Product.images)
            ).where(Product.id == product.id)
        )
        created_product = result.scalars().first()
        published_result = await db.execute(
            select(PublishedProduct).where(
                PublishedProduct.product_id == product.id,
                PublishedProduct.company_id == current_user.company_id,
                PublishedProduct.is_active == True
            )
        )
        _attach_ecommerce_state(created_product, published_result.scalars().first())
        return created_product
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
    ecommerce_data = _extract_ecommerce_payload(update_data)
    images_data = update_data.pop("images", None)
    
    for field, value in update_data.items():
        setattr(product, field, value)
    product.updated_by_id = current_user.id
        
    # Update images if provided
    if images_data is not None:
        from app.models.product_image import ProductImage
        # For simplicity, delete existing and re-create (or smart diff)
        # Smart diff: keep existing if URL matches? No, IDs are safer.
        # Simplest: Delete all and re-create. (Inefficient but robust for MVP)
        # Better: Frontend sends all images. We compare.
        
        # Let's delete all and re-add for now to guaranteed sync
        # But we need to be careful with CASCADE.
        # Actually, let's keep it simple: 
        # If images provided, remove old ones and add new ones.
        
        # Fetch existing images to delete
        result_imgs = await db.execute(select(ProductImage).where(ProductImage.product_id == product.id))
        existing_imgs = result_imgs.scalars().all()
        for img in existing_imgs:
            await db.delete(img)
            
        for img in images_data:
            # images_data is list of dicts because model_dump was called on parent
            # wait, model_dump(exclude_unset=True) returns dicts for nested models?
            # Yes. 
            # But product_in.images is List[ProductImageCreate]
            # If we popped from update_data (dict), it is list of dicts.
            new_img = ProductImage(**img, product_id=product.id)
            db.add(new_img)

    await _sync_product_ecommerce(
        db,
        product=product,
        company_id=current_user.company_id,
        ecommerce_data=ecommerce_data,
    )

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
            selectinload(Product.variants),
            selectinload(Product.images)
        ).where(Product.id == product.id)
    )
    updated_product = result.scalars().first()
    published_result = await db.execute(
        select(PublishedProduct).where(
            PublishedProduct.product_id == product.id,
            PublishedProduct.company_id == current_user.company_id,
            PublishedProduct.is_active == True
        )
    )
    _attach_ecommerce_state(updated_product, published_result.scalars().first())
    return updated_product

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
