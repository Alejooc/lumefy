from typing import Any, List
from uuid import UUID
from urllib.parse import urljoin, urlsplit
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import delete, func, or_, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import joinedload, load_only, selectinload
import json
import re

from app.core.database import get_db
from app.models.product import Product
from app.models.product_image import ProductImage
from app.models.product_variant import ProductVariant
from app.models.storefront import PublishedProduct, StoreCollectionProduct, Storefront
from app.models.invoice import InvoiceItem
from app.models.inventory import Inventory
from app.models.inventory_lot import InventoryLot
from app.models.inventory_movement import InventoryMovement
from app.models.manufacturing import BillOfMaterials, BillOfMaterialsLine, ManufacturingOrder
from app.models.pricelist_item import PriceListItem
from app.models.procurement import PurchaseRequestItem, SupplierQuoteItem
from app.models.purchase_item import PurchaseOrderItem
from app.models.return_order import ReturnOrderItem
from app.models.sale import SaleItem
from app.models.stock_take import StockTakeItem
from app.models.logistics import SalePackageItem
from app.models.integration import IntegrationRecordLink
from app.schemas import product as schemas
from app.schemas import product_variant as variant_schemas
from app.models.user import User
from app.core.permissions import PermissionChecker
from app.core.plan_limits import PlanLimitChecker
from app.core.audit import log_activity
from app.services.integration_service import (
    prune_orphaned_local_assets,
    remove_unreferenced_local_assets,
)

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
    keys = {"visible_in_ecommerce"}
    return {key: payload.pop(key) for key in list(payload.keys()) if key in keys}


async def _ensure_unique_sku(
    db: AsyncSession,
    *,
    company_id: str | None,
    sku: str | None,
    exclude_product_id: str | None = None,
) -> str | None:
    """Normalize a SKU and reject duplicates inside the current company."""
    normalized = (sku or "").strip()
    if not normalized:
        return None

    query = select(Product.id).where(
        Product.company_id == company_id,
        Product.is_active.is_(True),
        Product.sku.is_not(None),
        func.lower(func.trim(Product.sku)) == normalized.lower(),
    ).limit(1)
    if exclude_product_id:
        query = query.where(Product.id != exclude_product_id)
    if await db.scalar(query):
        raise HTTPException(
            status_code=409,
            detail=f"Ya existe un producto activo con el SKU '{normalized}' en esta empresa.",
        )
    return normalized


async def _available_storefront_slug(
    db: AsyncSession,
    *,
    storefront_id: str,
    product_id: str,
    product_name: str,
) -> str:
    """Generate a stable, store-local URL without making it editable per channel."""
    base_slug = _slugify(product_name)
    candidate = base_slug
    suffix = 2

    while True:
        result = await db.execute(
            select(PublishedProduct.id).where(
                PublishedProduct.storefront_id == storefront_id,
                PublishedProduct.slug == candidate,
                PublishedProduct.product_id != product_id,
            )
        )
        if result.scalar_one_or_none() is None:
            return candidate
        candidate = f"{base_slug}-{suffix}"
        suffix += 1


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

    if published_product:
        published_product.storefront_id = storefront.id
        published_product.is_published = True
        published_product.updated_by_id = product.updated_by_id
        db.add(published_product)
        return

    db.add(
        PublishedProduct(
            storefront_id=storefront.id,
            product_id=product.id,
            slug=await _available_storefront_slug(
                db,
                storefront_id=storefront.id,
                product_id=product.id,
                product_name=product.name,
            ),
            is_published=True,
            company_id=company_id,
            created_by_id=product.created_by_id,
            updated_by_id=product.updated_by_id,
        )
    )


def _attach_ecommerce_state(product: Product, published_product: PublishedProduct | None) -> None:
    product.visible_in_ecommerce = bool(published_product and published_product.is_published)


# A product is historical data once another business document points to it.  These
# checks keep the bulk operation useful (safe products are still removed) while
# protecting sales, inventory and accounting history from accidental deletion.
_PRODUCT_DELETE_RELATIONS = (
    ("Tiene una orden o venta asociada", SaleItem.product_id),
    ("Tiene una factura asociada", InvoiceItem.product_id),
    ("Tiene existencias registradas", Inventory.product_id),
    ("Tiene lotes de inventario registrados", InventoryLot.product_id),
    ("Tiene movimientos de inventario registrados", InventoryMovement.product_id),
    ("Tiene una orden de compra asociada", PurchaseOrderItem.product_id),
    ("Tiene una solicitud de compra asociada", PurchaseRequestItem.product_id),
    ("Tiene una cotización de proveedor asociada", SupplierQuoteItem.product_id),
    ("Tiene una devolución asociada", ReturnOrderItem.product_id),
    ("Tiene una lista de precios asociada", PriceListItem.product_id),
    ("Tiene un conteo de inventario asociado", StockTakeItem.product_id),
    ("Está publicado en ecommerce", PublishedProduct.product_id),
    ("Está usado como producto terminado en fabricación", BillOfMaterials.product_id),
    ("Está usado como componente en fabricación", BillOfMaterialsLine.component_id),
)


async def _find_product_delete_blockers(db: AsyncSession, product_ids: list[Any]) -> dict[Any, list[str]]:
    """Return the historical relations that make each product undeletable."""
    blockers: dict[Any, list[str]] = {product_id: [] for product_id in product_ids}
    if not product_ids:
        return blockers
    for reason, product_column in _PRODUCT_DELETE_RELATIONS:
        result = await db.execute(
            select(product_column).where(product_column.in_(product_ids)).distinct()
        )
        for product_id in result.scalars().all():
            if product_id in blockers and reason not in blockers[product_id]:
                blockers[product_id].append(reason)
    return blockers


async def _remove_ecommerce_publications(
    db: AsyncSession,
    *,
    company_id: Any,
    product_ids: list[Any],
) -> None:
    """Remove non-historical ecommerce rows before permanently deleting products."""
    if not product_ids:
        return

    published_result = await db.execute(
        select(PublishedProduct.id).where(
            PublishedProduct.company_id == company_id,
            PublishedProduct.product_id.in_(product_ids),
        )
    )
    published_ids = published_result.scalars().all()
    if not published_ids:
        return

    # Collection rows point to the publication, not directly to the product.
    # Delete them first because this relationship is not database-cascading in
    # every deployed schema.
    await db.execute(
        delete(StoreCollectionProduct).where(
            StoreCollectionProduct.published_product_id.in_(published_ids)
        )
    )
    await db.execute(
        delete(PublishedProduct).where(PublishedProduct.id.in_(published_ids))
    )


async def _purge_inventory_records(
    db: AsyncSession,
    *,
    company_id: Any,
    product_ids: list[Any],
) -> None:
    """Delete inventory state and inventory audit rows for archived products."""
    if not product_ids:
        return

    conditions = lambda model: (
        model.company_id == company_id,
        model.product_id.in_(product_ids),
    )

    # Stock-take lines, lots, movements and current balances all reference the
    # product directly. They must be removed before deleting its variants and
    # the product itself.
    for model in (StockTakeItem, InventoryLot, InventoryMovement, Inventory):
        await db.execute(delete(model).where(*conditions(model)))


async def _purge_catalog_dependencies(
    db: AsyncSession,
    *,
    company_id: Any,
    product_ids: list[Any],
    variant_ids: list[Any],
) -> dict[str, int]:
    """Remove every product-owned row before a deliberate catalog purge.

    The regular delete endpoints intentionally protect sales and accounting
    history.  This helper is only used by the explicitly confirmed
    ``/purge-all`` operation.  It removes product lines from those documents,
    while keeping their headers (sale, invoice, purchase, etc.) intact, so no
    foreign-key row can turn the requested physical deletion into an archive.
    """

    if not product_ids:
        return {}

    counts: dict[str, int] = {}

    async def remove(model: Any, condition: Any, label: str) -> None:
        # Product and variant UUIDs are globally unique. Filtering by those
        # foreign keys also handles legacy rows whose audit company_id was
        # never populated, while the selected IDs were already scoped to the
        # current company above.
        result = await db.execute(delete(model).where(condition))
        counts[label] = counts.get(label, 0) + int(result.rowcount or 0)

    # Ecommerce rows are metadata and must go before their collection links.
    published_ids = (
        await db.execute(
            select(PublishedProduct.id).where(
                PublishedProduct.company_id == company_id,
                PublishedProduct.product_id.in_(product_ids),
            )
        )
    ).scalars().all()
    if published_ids:
        result = await db.execute(
            delete(StoreCollectionProduct).where(
                StoreCollectionProduct.company_id == company_id,
                StoreCollectionProduct.published_product_id.in_(published_ids),
            )
        )
        counts["collection_links"] = int(result.rowcount or 0)
        result = await db.execute(
            delete(PublishedProduct).where(
                PublishedProduct.company_id == company_id,
                PublishedProduct.id.in_(published_ids),
            )
        )
        counts["published_products"] = int(result.rowcount or 0)

    # Remove shipping/return children before their sale lines.
    sale_item_ids = select(SaleItem.id).where(
        SaleItem.company_id == company_id,
        SaleItem.product_id.in_(product_ids),
    )
    await remove(SalePackageItem, SalePackageItem.sale_item_id.in_(sale_item_ids), "sale_package_items")
    await remove(
        ReturnOrderItem,
        or_(
            ReturnOrderItem.product_id.in_(product_ids),
            ReturnOrderItem.sale_item_id.in_(sale_item_ids),
        ),
        "return_order_items",
    )
    await remove(SaleItem, SaleItem.product_id.in_(product_ids), "sale_items")

    # Product lines in commercial documents are deliberately removed. The
    # parent documents remain available for navigation and can be reconciled
    # by the operator after a test-catalog reset.
    for model, label in (
        (InvoiceItem, "invoice_items"),
        (PurchaseOrderItem, "purchase_order_items"),
        (PurchaseRequestItem, "purchase_request_items"),
        (SupplierQuoteItem, "supplier_quote_items"),
        (PriceListItem, "pricelist_items"),
        (StockTakeItem, "stock_take_items"),
        (InventoryLot, "inventory_lots"),
        (InventoryMovement, "inventory_movements"),
        (Inventory, "inventory"),
    ):
        await remove(model, model.product_id.in_(product_ids), label)

    # Manufacturing orders point to BOMs, so remove those orders before BOM
    # lines/headers. Component lines are removed even when the BOM belongs to
    # a different product; otherwise the component FK would protect the row.
    bom_ids = (
        await db.execute(
            select(BillOfMaterials.id).where(
                BillOfMaterials.company_id == company_id,
                BillOfMaterials.product_id.in_(product_ids),
            )
        )
    ).scalars().all()
    if bom_ids:
        result = await db.execute(
            delete(ManufacturingOrder).where(
                ManufacturingOrder.company_id == company_id,
                ManufacturingOrder.bom_id.in_(bom_ids),
            )
        )
        counts["manufacturing_orders"] = int(result.rowcount or 0)
    await remove(
        BillOfMaterialsLine,
        or_(
            BillOfMaterialsLine.component_id.in_(product_ids),
            BillOfMaterialsLine.bom_id.in_(bom_ids) if bom_ids else False,
        ),
        "bill_of_materials_lines",
    )
    if bom_ids:
        result = await db.execute(
            delete(BillOfMaterials).where(
                BillOfMaterials.company_id == company_id,
                BillOfMaterials.id.in_(bom_ids),
            )
        )
        counts["bills_of_materials"] = int(result.rowcount or 0)

    # Links are source metadata, not business history. Delete them instead of
    # leaving stale SKU mappings that could make the next inventory run target
    # products that no longer exist.
    result = await db.execute(
        delete(IntegrationRecordLink).where(
            IntegrationRecordLink.company_id == company_id,
            or_(
                IntegrationRecordLink.local_product_id.in_(product_ids),
                IntegrationRecordLink.local_variant_id.in_(variant_ids) if variant_ids else False,
            ),
        )
    )
    counts["integration_links"] = int(result.rowcount or 0)

    if variant_ids:
        result = await db.execute(
            delete(ProductVariant).where(
                ProductVariant.company_id == company_id,
                ProductVariant.id.in_(variant_ids),
            )
        )
        counts["variants"] = int(result.rowcount or 0)

    # ProductImage has an ON DELETE CASCADE in the deployed schema. Explicitly
    # deleting it keeps the operation valid against older schemas as well.
    result = await db.execute(delete(ProductImage).where(ProductImage.product_id.in_(product_ids)))
    counts["images"] = int(result.rowcount or 0)
    result = await db.execute(
        delete(Product).where(Product.company_id == company_id, Product.id.in_(product_ids))
    )
    counts["products"] = int(result.rowcount or 0)
    return counts


async def _purge_products_physically(
    *,
    db: AsyncSession,
    product_ids: list[Any],
    current_user: User,
) -> schemas.ProductBulkDeleteResponse:
    """Delete the requested products and their product-owned relations.

    Product deletion is intentionally physical in the admin panel.  Sales,
    invoices and purchase headers remain available for navigation/audit, but
    their product lines, inventory rows and ecommerce publications are removed
    so a product the operator no longer wants cannot remain as an archive.
    """

    requested_ids = list(dict.fromkeys(product_ids))
    if not requested_ids:
        return schemas.ProductBulkDeleteResponse(
            requested=0,
            deleted=0,
            deleted_ids=[],
            blocked=[],
            not_found=[],
            archived=0,
            archived_ids=[],
        )

    result = await db.execute(
        select(Product.id).where(
            Product.company_id == current_user.company_id,
            Product.id.in_(requested_ids),
        )
    )
    found_ids = list(result.scalars().all())
    found_set = set(found_ids)
    not_found = [product_id for product_id in requested_ids if product_id not in found_set]
    if not found_ids:
        return schemas.ProductBulkDeleteResponse(
            requested=len(requested_ids),
            deleted=0,
            deleted_ids=[],
            blocked=[],
            not_found=not_found,
            archived=0,
            archived_ids=[],
        )

    variant_ids = list(
        (
            await db.execute(
                select(ProductVariant.id).where(ProductVariant.product_id.in_(found_ids))
            )
        ).scalars().all()
    )
    local_asset_urls: set[str] = {
        str(value).strip()
        for value in (
            await db.execute(select(Product.image_url).where(Product.id.in_(found_ids)))
        ).scalars().all()
        if value
    }
    local_asset_urls.update(
        str(value).strip()
        for value in (
            await db.execute(select(ProductImage.image_url).where(ProductImage.product_id.in_(found_ids)))
        ).scalars().all()
        if value
    )

    try:
        counts = await _purge_catalog_dependencies(
            db,
            company_id=current_user.company_id,
            product_ids=found_ids,
            variant_ids=variant_ids,
        )
        await log_activity(
            db,
            action="DELETE",
            entity_type="Product",
            entity_id=current_user.company_id,
            user_id=current_user.id,
            company_id=current_user.company_id,
            details={"bulk": len(found_ids) > 1, "physical": True, "products": len(found_ids)},
        )
        await db.commit()
    except Exception:
        await db.rollback()
        raise

    await remove_unreferenced_local_assets(db, local_asset_urls)
    await prune_orphaned_local_assets(db)
    deleted = counts.get("products", 0)
    return schemas.ProductBulkDeleteResponse(
        requested=len(requested_ids),
        deleted=deleted,
        deleted_ids=found_ids[:deleted],
        blocked=[],
        not_found=not_found,
        archived=0,
        archived_ids=[],
    )


def _delete_blocker_detail(product: Product, reasons: list[str]) -> str:
    return (
        f"No se puede eliminar '{product.name}' porque {', '.join(reasons).lower()}. "
        "Primero elimina o desvincula esas relaciones."
    )


def _product_filter_conditions(
    *,
    company_id: Any,
    search: str | None = None,
    category_id: str | None = None,
    brand_id: str | None = None,
    product_type: str | None = None,
    include_archived: bool = False,
):
    """Return reusable product predicates without eager-loading side effects."""
    conditions = []
    if company_id:
        conditions.append(Product.company_id == company_id)
    # Archived products remain in the database when they are referenced by
    # historical documents, but must disappear from the active catalog unless
    # an administrator explicitly requests the archived view.
    if not include_archived:
        conditions.append(Product.is_active.is_(True))

    if search:
        search_filter = f"%{search.strip()}%"
        conditions.append(
            or_(
                Product.name.ilike(search_filter),
                Product.sku.ilike(search_filter),
                Product.barcode.ilike(search_filter),
                Product.internal_reference.ilike(search_filter),
                Product.variants.any(
                    or_(
                        ProductVariant.name.ilike(search_filter),
                        ProductVariant.sku.ilike(search_filter),
                        ProductVariant.barcode.ilike(search_filter),
                    )
                ),
            )
        )

    if category_id:
        conditions.append(Product.category_id == category_id)
    if brand_id:
        conditions.append(Product.brand_id == brand_id)
    if product_type:
        conditions.append(Product.product_type == product_type)
    return conditions


def _product_collection_query(
    *,
    company_id: Any,
    search: str | None = None,
    category_id: str | None = None,
    brand_id: str | None = None,
    product_type: str | None = None,
    include_archived: bool = False,
):
    """Build the shared catalog query used by list and paginated endpoints."""
    query = select(Product).options(
        joinedload(Product.brand),
        joinedload(Product.category),
        selectinload(Product.unit_of_measure),
        selectinload(Product.purchase_uom),
        selectinload(Product.variants),
        selectinload(Product.images),
    )
    query = query.where(
        *_product_filter_conditions(
            company_id=company_id,
            search=search,
            category_id=category_id,
            brand_id=brand_id,
            product_type=product_type,
            include_archived=include_archived,
        )
    )

    # Stable ordering is important: records must not jump between pages while
    # the user navigates the catalog.
    return query.order_by(Product.created_at.desc(), Product.id.desc())


async def _attach_published_state(
    db: AsyncSession,
    products: list[Product],
    company_id: Any,
) -> list[Product]:
    if not products or not company_id:
        return products

    product_ids = [product.id for product in products]
    published_result = await db.execute(
        select(PublishedProduct).where(
            PublishedProduct.company_id == company_id,
            PublishedProduct.product_id.in_(product_ids),
            PublishedProduct.is_active == True,
        )
    )
    published_map = {item.product_id: item for item in published_result.scalars().all()}
    for product in products:
        _attach_ecommerce_state(product, published_map.get(product.id))
    return products

@router.get("/", response_model=List[schemas.Product])
async def read_products(
    db: AsyncSession = Depends(get_db),
    skip: int = 0,
    limit: int = 100,
    search: str = None,
    category_id: str = None,
    brand_id: str = None,
    product_type: str = None,
    include_archived: bool = False,
    current_user: User = Depends(PermissionChecker("view_products")),
) -> Any:
    """Retrieve products with all relations."""
    query = _product_collection_query(
        company_id=current_user.company_id,
        search=search,
        category_id=category_id,
        brand_id=brand_id,
        product_type=product_type,
        include_archived=include_archived,
    ).offset(skip).limit(limit)
    result = await db.execute(query)
    products = result.scalars().all()
    return await _attach_published_state(db, products, current_user.company_id)


@router.get("/paged", response_model=schemas.ProductPage)
async def read_products_page(
    db: AsyncSession = Depends(get_db),
    page: int = 1,
    page_size: int = 100,
    search: str = None,
    category_id: str = None,
    brand_id: str = None,
    product_type: str = None,
    include_archived: bool = False,
    current_user: User = Depends(PermissionChecker("view_products")),
) -> schemas.ProductPage:
    """Retrieve a catalog page together with the total matching product count."""
    if page < 1:
        raise HTTPException(status_code=422, detail="La página debe ser mayor o igual a 1.")
    if page_size < 1 or page_size > 100:
        raise HTTPException(status_code=422, detail="El tamaño de página debe estar entre 1 y 100.")

    filters = {
        "company_id": current_user.company_id,
        "search": search,
        "category_id": category_id,
        "brand_id": brand_id,
        "product_type": product_type,
        "include_archived": include_archived,
    }
    # Count active and complete-catalog rows in one lightweight query. The
    # previous implementation built the full eager-loaded collection query
    # before counting, and two separate counts would add another round trip
    # on every page/search request.
    count_filters = {**filters, "include_archived": True}
    count_row = (
        await db.execute(
            select(
                func.count(Product.id).label("catalog_total"),
                func.count(Product.id)
                .filter(Product.is_active.is_(True))
                .label("active_total"),
            ).where(*_product_filter_conditions(**count_filters))
        )
    ).one()
    total_catalog = int(count_row.catalog_total or 0)
    total = total_catalog if include_archived else int(count_row.active_total or 0)
    total_pages = (total + page_size - 1) // page_size if total else 0
    page = min(page, total_pages) if total_pages else 1

    result = await db.execute(
        select(Product, func.count(ProductVariant.id).label("variant_count"))
        .outerjoin(ProductVariant, ProductVariant.product_id == Product.id)
        .options(
            load_only(
                Product.id,
                Product.company_id,
                Product.is_active,
                Product.name,
                Product.internal_reference,
                Product.sku,
                Product.barcode,
                Product.image_url,
                Product.product_type,
                Product.price,
                Product.cost,
                Product.track_inventory,
                Product.category_id,
                Product.brand_id,
            ),
            # Keep these as select-in loads: joinedload would add category and
            # brand columns to the grouped count query and break PostgreSQL's
            # GROUP BY validation.
            selectinload(Product.brand),
            selectinload(Product.category),
        )
        .where(*_product_filter_conditions(**filters))
        .group_by(Product.id)
        .order_by(Product.created_at.desc(), Product.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    rows = result.all()
    products = await _attach_published_state(
        db, [row[0] for row in rows], current_user.company_id
    )
    items = []
    for product, row in zip(products, rows):
        item = schemas.ProductListItem.model_validate(product)
        item.variant_count = int(row.variant_count or 0)
        items.append(item)
    return schemas.ProductPage(
        items=items,
        total=total,
        total_catalog=total_catalog,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )

_PRODUCT_EXPORT_COLUMNS = {
    "product_id": "product_id",
    "variant_id": "variant_id",
    "name": "name",
    "sku": "sku",
    "barcode": "barcode",
    "variant_name": "variant_name",
    "variant_sku": "variant_sku",
    "variant_barcode": "variant_barcode",
    "price": "price",
    "cost": "cost",
    "price_extra": "price_extra",
    "cost_extra": "cost_extra",
    "variant_price": "variant_price",
    "variant_cost": "variant_cost",
    "variant_attributes_json": "variant_attributes_json",
    "variant_weight": "variant_weight",
    "product_type": "product_type",
    "category_name": "category_name",
    "brand_name": "brand_name",
    "image_url": "image_url",
    "tax_rate": "tax_rate",
    "min_stock": "min_stock",
    "track_inventory": "track_inventory",
    "sale_ok": "sale_ok",
    "purchase_ok": "purchase_ok",
    "is_active": "is_active",
    "variant_is_active": "variant_is_active",
}


def _product_export_row(product: Product, variant: ProductVariant | None = None) -> dict[str, Any]:
    """Build one round-trip row for a product or one of its variants.

    IDs are the only stable relation keys.  SKU values are deliberately kept as
    editable business data and are never used to decide which record to update.
    """
    return {
        "product_id": str(product.id),
        "variant_id": str(variant.id) if variant else "",
        "name": product.name or "",
        "sku": product.sku or "",
        "barcode": product.barcode or "",
        "variant_name": variant.name if variant else "",
        "variant_sku": variant.sku if variant else "",
        "variant_barcode": variant.barcode if variant else "",
        "price": float(product.price) if product.price is not None else 0,
        "cost": float(product.cost) if product.cost is not None else 0,
        "price_extra": float(variant.price_extra) if variant else 0,
        "cost_extra": float(variant.cost_extra) if variant else 0,
        "variant_price": float(variant.price) if variant and variant.price is not None else "",
        "variant_cost": float(variant.cost) if variant and variant.cost is not None else "",
        "variant_attributes_json": (
            json.dumps(variant.attributes or {}, ensure_ascii=False, sort_keys=True)
            if variant
            else ""
        ),
        "variant_weight": float(variant.weight) if variant and variant.weight is not None else "",
        "product_type": product.product_type or "",
        "category_name": product.category.name if product.category else "",
        "brand_name": product.brand.name if product.brand else "",
        "image_url": product.image_url or "",
        "tax_rate": float(product.tax_rate) if product.tax_rate is not None else 0,
        "min_stock": float(product.min_stock) if product.min_stock is not None else 0,
        "track_inventory": bool(product.track_inventory),
        "sale_ok": bool(product.sale_ok),
        "purchase_ok": bool(product.purchase_ok),
        "is_active": bool(product.is_active),
        "variant_is_active": bool(variant.is_active) if variant else "",
    }


def _build_product_export_rows(products: list[Product]) -> list[dict[str, Any]]:
    """Return one row per variant, or one row for products without variants."""
    rows: list[dict[str, Any]] = []
    for product in products:
        variants = list(product.variants or [])
        if variants:
            rows.extend(_product_export_row(product, variant) for variant in variants)
        else:
            rows.append(_product_export_row(product))
    return rows


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
        selectinload(Product.variants),
    )
    if current_user.company_id:
        query = query.where(Product.company_id == current_user.company_id)
    if search:
        search_filter = f"%{search}%"
        query = query.where(
            or_(
                Product.name.ilike(search_filter),
                Product.sku.ilike(search_filter),
                Product.variants.any(ProductVariant.name.ilike(search_filter)),
                Product.variants.any(ProductVariant.sku.ilike(search_filter)),
                Product.variants.any(ProductVariant.barcode.ilike(search_filter)),
            )
        )
    if category_id:
        query = query.where(Product.category_id == category_id)
    if brand_id:
        query = query.where(Product.brand_id == brand_id)

    result = await db.execute(query)
    products = result.scalars().all()

    rows = _build_product_export_rows(products)
    columns = _PRODUCT_EXPORT_COLUMNS

    if format == "csv":
        return ExportService.to_csv_response(rows, columns, filename="productos")
    return ExportService.to_excel_response(rows, columns, filename="productos")


def _complete_relative_image_url(
    value: str | None,
    prefix: str,
    *,
    replace_existing: bool = False,
) -> tuple[str | None, bool]:
    """Return an image URL under ``prefix``.

    Relative values are always completed. Absolute values are deliberately
    preserved unless ``replace_existing`` is enabled. In replacement mode the
    complete provider path is retained while only the old host/base is
    discarded. This is important for values such as
    ``products/12529/9_b4.jpg``: the directory segments must not be lost.
    """
    normalized = (value or "").strip()
    if not normalized:
        return value, False

    parsed = urlsplit(normalized)
    is_absolute = parsed.scheme in {"http", "https"} and parsed.netloc
    if is_absolute and not replace_existing:
        return normalized, False

    if is_absolute:
        # Keep the complete path returned by the provider, not only its
        # filename. For example, old-base/products/12529/9_b4.jpg becomes
        # new-base/products/12529/9_b4.jpg.
        path = parsed.path.lstrip("/")
        if not path:
            return normalized, False
    else:
        path = normalized.lstrip("/")

    completed = urljoin(prefix.rstrip("/") + "/", path)
    return completed, completed != normalized


@router.post("/bulk-complete-image-urls", response_model=schemas.ProductBulkImageUrlResponse)
async def bulk_complete_image_urls(
    *,
    product_in: schemas.ProductBulkImageUrlRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(PermissionChecker("manage_inventory")),
) -> schemas.ProductBulkImageUrlResponse:
    """Complete image paths and optionally replace an incorrect old URL base."""
    prefix = product_in.prefix.strip()
    parsed_prefix = urlsplit(prefix)
    if parsed_prefix.scheme not in {"http", "https"} or not parsed_prefix.netloc:
        raise HTTPException(
            status_code=422,
            detail="La base debe ser una URL completa, por ejemplo https://cdn.proveedor.com/. Se concatenará con la ruta de imagen que entregue el proveedor.",
        )

    requested_ids = list(dict.fromkeys(product_in.product_ids or []))
    query = select(Product).options(selectinload(Product.images)).where(
        Product.company_id == current_user.company_id,
    )
    if requested_ids:
        query = query.where(Product.id.in_(requested_ids))

    result = await db.execute(query)
    products = result.scalars().all()
    found_ids = {product.id for product in products}
    not_found = [product_id for product_id in requested_ids if product_id not in found_ids]
    products_updated = 0
    images_updated = 0
    skipped_valid = 0

    for product in products:
        changed = False
        product_url, product_changed = _complete_relative_image_url(
            product.image_url,
            prefix,
            replace_existing=product_in.replace_existing,
        )
        if product_changed:
            product.image_url = product_url
            changed = True
            images_updated += 1
        elif product.image_url:
            skipped_valid += 1

        for image in product.images:
            image_url, image_changed = _complete_relative_image_url(
                image.image_url,
                prefix,
                replace_existing=product_in.replace_existing,
            )
            if image_changed:
                image.image_url = image_url
                changed = True
                images_updated += 1
            elif image.image_url:
                skipped_valid += 1

        if changed:
            products_updated += 1

    await db.commit()
    return schemas.ProductBulkImageUrlResponse(
        requested=len(requested_ids) if requested_ids else len(products),
        products_updated=products_updated,
        images_updated=images_updated,
        skipped_valid=skipped_valid,
        not_found=not_found,
    )


@router.post("/bulk-publish", response_model=schemas.ProductBulkPublishResponse)
async def bulk_publish_products(
    *,
    product_in: schemas.ProductBulkPublishRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(PermissionChecker("manage_inventory")),
) -> schemas.ProductBulkPublishResponse:
    """Publish selected products, or the complete active catalog, in the primary store."""
    storefront = await _get_primary_storefront(db, current_user.company_id)
    if not storefront:
        raise HTTPException(
            status_code=400,
            detail="Primero configura y activa una tienda ecommerce.",
        )

    requested_ids = list(dict.fromkeys(product_in.product_ids or []))
    query = select(Product).where(
        Product.company_id == current_user.company_id,
        Product.is_active == True,
    )
    if requested_ids:
        query = query.where(Product.id.in_(requested_ids))
    query = query.order_by(Product.created_at.asc(), Product.id.asc())
    result = await db.execute(query)
    products = result.scalars().all()

    found_ids = {product.id for product in products}
    not_found = [product_id for product_id in requested_ids if product_id not in found_ids]
    published_result = await db.execute(
        select(PublishedProduct).where(
            PublishedProduct.company_id == current_user.company_id,
            PublishedProduct.storefront_id == storefront.id,
        )
    )
    existing = {item.product_id: item for item in published_result.scalars().all()}
    used_slugs = {item.slug for item in existing.values() if item.slug}

    published = 0
    reactivated = 0
    already_published = 0
    for product in products:
        published_product = existing.get(product.id)
        if published_product:
            was_published = bool(published_product.is_active and published_product.is_published)
            published_product.is_active = True
            published_product.is_published = True
            published_product.updated_by_id = current_user.id
            if was_published:
                already_published += 1
            else:
                reactivated += 1
            published += 1
            continue

        base_slug = _slugify(product.name)
        slug = base_slug
        suffix = 2
        while slug in used_slugs:
            slug = f"{base_slug}-{suffix}"
            suffix += 1
        used_slugs.add(slug)
        db.add(
            PublishedProduct(
                storefront_id=storefront.id,
                product_id=product.id,
                slug=slug,
                is_published=True,
                is_active=True,
                company_id=current_user.company_id,
                created_by_id=current_user.id,
                updated_by_id=current_user.id,
            )
        )
        published += 1

    await log_activity(
        db,
        action="PUBLISH",
        entity_type="Product",
        entity_id=current_user.company_id,
        user_id=current_user.id,
        company_id=current_user.company_id,
        details={
            "bulk": True,
            "requested": len(requested_ids) if requested_ids else len(products),
            "published": published,
        },
    )
    await db.commit()
    return schemas.ProductBulkPublishResponse(
        requested=len(requested_ids) if requested_ids else len(products),
        published=published,
        reactivated=reactivated,
        already_published=already_published,
        not_found=not_found,
    )


@router.post("/bulk-delete", response_model=schemas.ProductBulkDeleteResponse)
async def bulk_delete_products(
    *,
    product_in: schemas.ProductBulkDeleteRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(PermissionChecker("manage_inventory")),
) -> schemas.ProductBulkDeleteResponse:
    """Physically delete the selected products and their owned relations."""
    # Keep the response deterministic and do not process the same product twice
    # if a client accidentally submits duplicate checkbox values.
    product_ids = list(dict.fromkeys(product_in.product_ids))
    return await _purge_products_physically(
        db=db,
        product_ids=product_ids,
        current_user=current_user,
    )


async def _delete_products_guarded(
    *,
    db: AsyncSession,
    product_ids: list[Any],
    products_by_id: dict[Any, Product],
    not_found: list[Any],
    current_user: User,
    archive_blocked: bool = False,
) -> schemas.ProductBulkDeleteResponse:
    """Delete eligible products and optionally archive protected history."""
    blockers = await _find_product_delete_blockers(db, list(products_by_id))

    deleted_ids = []
    archived_ids = []
    blocked = []
    local_asset_urls_to_cleanup: set[str] = set()
    if archive_blocked:
        blocked_product_ids = [product_id for product_id, reasons in blockers.items() if reasons]
        if blocked_product_ids:
            # Remove archived products from every ecommerce channel in one
            # statement without touching the orders that reference them.
            await db.execute(
                update(PublishedProduct)
                .where(
                    PublishedProduct.company_id == current_user.company_id,
                    PublishedProduct.product_id.in_(blocked_product_ids),
                )
                .values(is_active=False, is_published=False)
            )

    try:
        for product_id in product_ids:
            product = products_by_id.get(product_id)
            if product is None:
                continue

            reasons = blockers.get(product_id, [])
            if reasons:
                if archive_blocked:
                    # Historical rows keep their product reference, so sales,
                    # invoices and inventory remain auditable. The product is
                    # removed from the active catalog and cannot be sold again.
                    product.is_active = False
                    product.sale_ok = False
                    product.purchase_ok = False
                    for variant in product.variants:
                        variant.is_active = False
                    archived_ids.append(product.id)
                    await log_activity(
                        db,
                        action="ARCHIVE",
                        entity_type="Product",
                        entity_id=product.id,
                        user_id=current_user.id,
                        company_id=current_user.company_id,
                        details={"bulk": True, "name": product.name, "reason": "force_delete"},
                    )
                    continue
                blocked.append(
                    schemas.ProductBulkDeleteBlocked(
                        id=product.id,
                        name=product.name,
                        reasons=reasons,
                    )
                )
                continue

            # A savepoint makes an unexpected database-level relation safe: one
            # problematic row is reported as blocked without rolling back other
            # products that were eligible for deletion.
            local_asset_urls_to_cleanup.update(
                str(value).strip()
                for value in [
                    product.image_url,
                    *(image.image_url for image in product.images),
                ]
                if value
            )
            try:
                async with db.begin_nested():
                    for variant in product.variants:
                        await db.delete(variant)
                    await db.delete(product)
                    await db.flush()
            except IntegrityError:
                blocked.append(
                    schemas.ProductBulkDeleteBlocked(
                        id=product.id,
                        name=product.name,
                        reasons=["Tiene una relación protegida por la base de datos"],
                    )
                )
                continue

            deleted_ids.append(product.id)
            await log_activity(
                db,
                action="DELETE",
                entity_type="Product",
                entity_id=product.id,
                user_id=current_user.id,
                company_id=current_user.company_id,
                details={"bulk": True, "name": product.name},
            )

        await db.commit()
        await remove_unreferenced_local_assets(db, local_asset_urls_to_cleanup)
        await prune_orphaned_local_assets(db)
    except Exception:
        await db.rollback()
        raise

    return schemas.ProductBulkDeleteResponse(
        requested=len(product_ids),
        deleted=len(deleted_ids),
        deleted_ids=deleted_ids,
        archived=len(archived_ids),
        archived_ids=archived_ids,
        blocked=blocked,
        not_found=not_found,
    )


@router.post("/bulk-delete-all", response_model=schemas.ProductBulkDeleteResponse)
async def bulk_delete_all_products(
    *,
    product_in: schemas.ProductBulkDeleteAllRequest | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(PermissionChecker("manage_inventory")),
) -> schemas.ProductBulkDeleteResponse:
    """Physically delete every product in the company, including archives."""
    product_in = product_in or schemas.ProductBulkDeleteAllRequest()
    query = (
        select(Product.id)
        .where(Product.company_id == current_user.company_id)
    )
    if product_in.search:
        search_filter = f"%{product_in.search}%"
        query = query.where(
            or_(
                Product.name.ilike(search_filter),
                Product.sku.ilike(search_filter),
                Product.barcode.ilike(search_filter),
                Product.internal_reference.ilike(search_filter),
            )
        )
    if product_in.category_id:
        query = query.where(Product.category_id == product_in.category_id)
    if product_in.brand_id:
        query = query.where(Product.brand_id == product_in.brand_id)
    if product_in.product_type:
        query = query.where(Product.product_type == product_in.product_type)

    result = await db.execute(query.order_by(Product.created_at.asc(), Product.id.asc()))
    return await _purge_products_physically(
        db=db,
        product_ids=list(result.scalars().all()),
        current_user=current_user,
    )


@router.post("/purge-all", response_model=schemas.ProductBulkDeleteResponse)
async def purge_all_products(
    *,
    product_in: schemas.ProductPurgeAllRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(PermissionChecker("manage_inventory")),
) -> schemas.ProductBulkDeleteResponse:
    """Physically empty the company catalog after an explicit confirmation.

    This is intentionally not wired to the legacy ``force`` flag: that flag
    used to archive products with history and was the source of the confusing
    behaviour in the admin panel. The purge is a separate, unmistakable
    destructive action.
    """

    conditions = _product_filter_conditions(
        company_id=current_user.company_id,
        search=product_in.search,
        category_id=str(product_in.category_id) if product_in.category_id else None,
        brand_id=str(product_in.brand_id) if product_in.brand_id else None,
        product_type=product_in.product_type,
        include_archived=True,
    )
    result = await db.execute(
        select(Product.id).where(*conditions).order_by(Product.created_at.asc(), Product.id.asc())
    )
    return await _purge_products_physically(
        db=db,
        product_ids=list(result.scalars().all()),
        current_user=current_user,
    )


@router.post("/bulk-restore-archived", response_model=schemas.ProductBulkRestoreArchivedResponse)
async def bulk_restore_archived_products(
    *,
    product_in: schemas.ProductBulkRestoreArchivedRequest | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(PermissionChecker("manage_inventory")),
) -> schemas.ProductBulkRestoreArchivedResponse:
    """Restore selected archived products, or the complete archived catalog."""
    product_in = product_in or schemas.ProductBulkRestoreArchivedRequest()
    requested_ids = list(dict.fromkeys(product_in.product_ids))
    query = (
        select(Product)
        .options(selectinload(Product.variants))
        .where(
            Product.company_id == current_user.company_id,
            Product.is_active.is_(False),
        )
    )
    if requested_ids:
        query = query.where(Product.id.in_(requested_ids))

    products = (await db.execute(query)).scalars().all()
    products_by_id = {product.id: product for product in products}
    not_found = [product_id for product_id in requested_ids if product_id not in products_by_id]

    for product in products:
        product.is_active = True
        product.sale_ok = True
        product.purchase_ok = True
        for variant in product.variants:
            variant.is_active = True

    if products:
        await log_activity(
            db,
            action="RESTORE",
            entity_type="Product",
            entity_id=current_user.company_id,
            user_id=current_user.id,
            company_id=current_user.company_id,
            details={
                "bulk": True,
                "restored": len(products),
                "product_ids": [str(product.id) for product in products],
            },
        )
    await db.commit()

    return schemas.ProductBulkRestoreArchivedResponse(
        requested=len(requested_ids) if requested_ids else len(products),
        restored=len(products),
        restored_ids=[product.id for product in products],
        not_found=not_found,
    )


@router.post("/bulk-delete-archived", response_model=schemas.ProductBulkDeleteResponse)
async def bulk_delete_archived_products(
    *,
    product_in: schemas.ProductBulkDeleteArchivedRequest | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(PermissionChecker("manage_inventory")),
) -> schemas.ProductBulkDeleteResponse:
    """Permanently delete selected archived products, or one archived batch."""
    product_in = product_in or schemas.ProductBulkDeleteArchivedRequest()
    requested_ids = list(dict.fromkeys(product_in.product_ids))
    query = (
        select(Product.id)
        .where(
            Product.company_id == current_user.company_id,
            Product.is_active.is_(False),
        )
    )
    if requested_ids:
        query = query.where(Product.id.in_(requested_ids))
    else:
        if product_in.exclude_product_ids:
            query = query.where(Product.id.not_in(product_in.exclude_product_ids))
        query = query.order_by(Product.created_at.asc(), Product.id.asc()).limit(product_in.limit)

    result = await db.execute(query)
    return await _purge_products_physically(
        db=db,
        product_ids=list(result.scalars().all()),
        current_user=current_user,
    )


@router.get("/{product_id}", response_model=schemas.Product)
async def read_product(
    product_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(PermissionChecker("view_products")),
) -> Any:
    """Get a single product with all relations."""
    result = await db.execute(
        select(Product).options(
            joinedload(Product.brand),
            joinedload(Product.unit_of_measure),
            joinedload(Product.purchase_uom),
            joinedload(Product.category),
            selectinload(Product.variants),
            selectinload(Product.images),
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

        product_data["sku"] = await _ensure_unique_sku(
            db,
            company_id=current_user.company_id,
            sku=product_data.get("sku"),
        )
        if ecommerce_data.get("visible_in_ecommerce") and not await _get_primary_storefront(
            db, current_user.company_id
        ):
            raise HTTPException(
                status_code=400,
                detail="Primero configura una tienda ecommerce para publicar productos.",
            )
        
        product = Product(**product_data, company_id=current_user.company_id, created_by_id=current_user.id, updated_by_id=current_user.id)
        db.add(product)
        await db.flush()
        
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
    except HTTPException:
        await db.rollback()
        raise
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=409, detail="Ya existe un producto con ese SKU en esta empresa.")
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

    if "sku" in update_data:
        update_data["sku"] = await _ensure_unique_sku(
            db,
            company_id=current_user.company_id,
            sku=update_data.get("sku"),
            exclude_product_id=str(product.id),
        )
    
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
    """Physically delete a product, including its product-owned relations."""
    result = await _purge_products_physically(
        db=db,
        product_ids=[product_id],
        current_user=current_user,
    )
    if result.not_found:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    return {"ok": True, "deleted": result.deleted}

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

_IMPORT_MISSING = object()


def _normalize_import_column(value: Any) -> str:
    """Normalize old Spanish export headers and the new machine headers."""
    import unicodedata

    text = unicodedata.normalize("NFKD", str(value))
    text = "".join(char for char in text if not unicodedata.combining(char))
    return re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")


_IMPORT_COLUMN_ALIASES = {
    "id_producto": "product_id",
    "producto_id": "product_id",
    "product_id": "product_id",
    "id_variante": "variant_id",
    "variante_id": "variant_id",
    "variant_id": "variant_id",
    "nombre": "name",
    "nombre_producto": "name",
    "product_name": "name",
    "name": "name",
    "sku_producto": "sku",
    "product_sku": "sku",
    "sku": "sku",
    "codigo_barras": "barcode",
    "barcode": "barcode",
    "nombre_variante": "variant_name",
    "variant_name": "variant_name",
    "sku_variante": "variant_sku",
    "variant_sku": "variant_sku",
    "codigo_barras_variante": "variant_barcode",
    "variant_barcode": "variant_barcode",
    "precio": "price",
    "precio_venta": "price",
    "sale_price": "price",
    "price": "price",
    "costo": "cost",
    "precio_costo": "cost",
    "cost_price": "cost",
    "cost": "cost",
    "precio_extra": "price_extra",
    "price_extra": "price_extra",
    "costo_extra": "cost_extra",
    "cost_extra": "cost_extra",
    "precio_variante": "variant_price",
    "variant_price": "variant_price",
    "costo_variante": "variant_cost",
    "variant_cost": "variant_cost",
    "atributos_variante_json": "variant_attributes_json",
    "variant_attributes_json": "variant_attributes_json",
    "peso_variante": "variant_weight",
    "variant_weight": "variant_weight",
    "tipo": "product_type",
    "product_type": "product_type",
    "categoria": "category_name",
    "categoria_nombre": "category_name",
    "category_name": "category_name",
    "marca": "brand_name",
    "marca_nombre": "brand_name",
    "brand_name": "brand_name",
    "imagen": "image_url",
    "imagen_url": "image_url",
    "image_url": "image_url",
    "tasa_impuesto": "tax_rate",
    "tax_rate": "tax_rate",
    "stock_minimo": "min_stock",
    "min_stock": "min_stock",
    "control_inventario": "track_inventory",
    "track_inventory": "track_inventory",
    "venta": "sale_ok",
    "sale_ok": "sale_ok",
    "compra": "purchase_ok",
    "purchase_ok": "purchase_ok",
    "activo": "is_active",
    "is_active": "is_active",
    "variante_activa": "variant_is_active",
    "variant_is_active": "variant_is_active",
}


def _normalize_import_dataframe(df: Any) -> Any:
    rename_map = {}
    for column in df.columns:
        normalized = _normalize_import_column(column)
        rename_map[column] = _IMPORT_COLUMN_ALIASES.get(normalized, normalized)
    return df.rename(columns=rename_map)


def _import_row_value(row: Any, key: str) -> Any:
    if key not in row.index:
        return _IMPORT_MISSING
    value = row[key]
    if value is None:
        return None
    try:
        if bool(__import__("pandas").isna(value)):
            return None
    except (TypeError, ValueError):
        pass
    if isinstance(value, str):
        return value.strip() or None
    return value


def _import_text(value: Any, *, default: Any = _IMPORT_MISSING) -> Any:
    if value is _IMPORT_MISSING:
        return default
    if value is None:
        return None
    return str(value).strip() or None


def _import_float(value: Any, *, default: Any = _IMPORT_MISSING) -> Any:
    if value is _IMPORT_MISSING or value is None:
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        raise ValueError(f"'{value}' no es un número válido")


def _import_bool(value: Any, *, default: Any = _IMPORT_MISSING) -> Any:
    if value is _IMPORT_MISSING or value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    normalized = str(value).strip().lower()
    if normalized in {"1", "true", "t", "yes", "si", "sí", "x"}:
        return True
    if normalized in {"0", "false", "f", "no", "n"}:
        return False
    raise ValueError(f"'{value}' no es un booleano válido")


def _import_uuid(value: Any, field_name: str) -> UUID | None:
    if value is _IMPORT_MISSING or value is None:
        return None
    try:
        return UUID(str(value).strip())
    except (ValueError, AttributeError):
        raise ValueError(f"{field_name} debe ser un UUID válido")


def _import_json(value: Any) -> dict[str, Any] | None:
    if value is _IMPORT_MISSING or value is None:
        return None
    if isinstance(value, dict):
        return value
    try:
        parsed = json.loads(str(value))
    except (TypeError, json.JSONDecodeError):
        raise ValueError("variant_attributes_json debe contener JSON válido")
    if not isinstance(parsed, dict):
        raise ValueError("variant_attributes_json debe ser un objeto JSON")
    return parsed


async def _get_import_category_id(
    db: AsyncSession,
    category_map: dict[str, UUID],
    category_name: Any,
    company_id: UUID | None,
) -> UUID | None:
    name = _import_text(category_name, default=None)
    if not name:
        return None
    key = name.casefold()
    if key in category_map:
        return category_map[key]
    from app.models.category import Category

    new_category = Category(name=name, company_id=company_id)
    db.add(new_category)
    await db.flush()
    category_map[key] = new_category.id
    return new_category.id


def _apply_product_import_values(product: Product, row: Any) -> None:
    text_fields = {
        "name": "name",
        "sku": "sku",
        "barcode": "barcode",
        "product_type": "product_type",
        "image_url": "image_url",
    }
    for column, attribute in text_fields.items():
        value = _import_row_value(row, column)
        if value is not _IMPORT_MISSING:
            setattr(product, attribute, _import_text(value, default=None))

    numeric_fields = {
        "price": "price",
        "cost": "cost",
        "tax_rate": "tax_rate",
        "min_stock": "min_stock",
    }
    for column, attribute in numeric_fields.items():
        value = _import_float(_import_row_value(row, column), default=_IMPORT_MISSING)
        if value is not _IMPORT_MISSING:
            setattr(product, attribute, value)

    for column, attribute in {
        "track_inventory": "track_inventory",
        "sale_ok": "sale_ok",
        "purchase_ok": "purchase_ok",
        "is_active": "is_active",
    }.items():
        value = _import_bool(_import_row_value(row, column), default=_IMPORT_MISSING)
        if value is not _IMPORT_MISSING:
            setattr(product, attribute, value)


def _apply_variant_import_values(variant: ProductVariant, row: Any) -> None:
    text_fields = {
        "variant_name": "name",
        "variant_sku": "sku",
        "variant_barcode": "barcode",
    }
    for column, attribute in text_fields.items():
        value = _import_row_value(row, column)
        if value is not _IMPORT_MISSING:
            setattr(variant, attribute, _import_text(value, default=None))

    for column, attribute in {
        "price_extra": "price_extra",
        "cost_extra": "cost_extra",
        "variant_price": "price",
        "variant_cost": "cost",
        "variant_weight": "weight",
    }.items():
        value = _import_float(_import_row_value(row, column), default=_IMPORT_MISSING)
        if value is not _IMPORT_MISSING:
            setattr(variant, attribute, value)

    attributes = _import_json(_import_row_value(row, "variant_attributes_json"))
    if attributes is not None:
        variant.attributes = attributes
    active = _import_bool(_import_row_value(row, "variant_is_active"), default=_IMPORT_MISSING)
    if active is not _IMPORT_MISSING:
        variant.is_active = active


@router.post("/import", response_model=dict)
async def import_products(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(PermissionChecker("manage_inventory")),
) -> Any:
    """Create or update products/variants using IDs from the export."""
    import io
    import pandas as pd

    filename = (file.filename or "").lower()
    if not filename.endswith((".csv", ".xls", ".xlsx")):
        raise HTTPException(status_code=400, detail="Formato de archivo inválido. Use CSV o Excel.")

    try:
        content = await file.read()
        if filename.endswith(".csv"):
            dataframe = pd.read_csv(io.BytesIO(content))
        else:
            dataframe = pd.read_excel(io.BytesIO(content))
        dataframe = _normalize_import_dataframe(dataframe)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"No se pudo leer el archivo: {exc}") from exc

    from app.models.category import Category

    result = await db.execute(select(Category).where(Category.company_id == current_user.company_id))
    category_map = {category.name.casefold(): category.id for category in result.scalars().all()}

    processed = 0
    products_created = 0
    products_updated: set[UUID] = set()
    variants_created = 0
    variants_updated: set[UUID] = set()
    errors: list[str] = []

    for index, row in dataframe.iterrows():
        row_product_created = False
        row_product_updated: UUID | None = None
        row_variant_created = False
        row_variant_updated: UUID | None = None
        try:
            async with db.begin_nested():
                product_id = _import_uuid(_import_row_value(row, "product_id"), "product_id")
                variant_id = _import_uuid(_import_row_value(row, "variant_id"), "variant_id")
                if variant_id and not product_id:
                    raise ValueError("variant_id requiere product_id")

                if product_id:
                    product_result = await db.execute(
                        select(Product).where(
                            Product.id == product_id,
                            Product.company_id == current_user.company_id,
                        )
                    )
                    product = product_result.scalars().first()
                    if not product:
                        raise ValueError("product_id no pertenece a esta empresa o no existe")
                    row_product_updated = product.id
                else:
                    name = _import_text(_import_row_value(row, "name"), default=None)
                    if not name:
                        raise ValueError("name es obligatorio para crear un producto")
                    product = Product(
                        name=name,
                        company_id=current_user.company_id,
                        price=_import_float(_import_row_value(row, "price"), default=0.0),
                        cost=_import_float(_import_row_value(row, "cost"), default=0.0),
                        min_stock=_import_float(_import_row_value(row, "min_stock"), default=0.0),
                        track_inventory=_import_bool(_import_row_value(row, "track_inventory"), default=True),
                    )
                    db.add(product)
                    await db.flush()
                    row_product_created = True

                _apply_product_import_values(product, row)
                category_name = _import_row_value(row, "category_name")
                if category_name is not _IMPORT_MISSING and category_name is not None:
                    product.category_id = await _get_import_category_id(
                        db, category_map, category_name, current_user.company_id
                    )

                if variant_id:
                    variant_result = await db.execute(
                        select(ProductVariant).where(
                            ProductVariant.id == variant_id,
                            ProductVariant.product_id == product.id,
                        )
                    )
                    variant = variant_result.scalars().first()
                    if not variant:
                        raise ValueError("variant_id no pertenece al product_id indicado o no existe")
                    row_variant_updated = variant.id
                    _apply_variant_import_values(variant, row)
                else:
                    variant_name = _import_text(_import_row_value(row, "variant_name"), default=None)
                    variant_sku = _import_text(_import_row_value(row, "variant_sku"), default=None)
                    if variant_name or variant_sku:
                        if not variant_name:
                            raise ValueError("variant_name es obligatorio para crear una variante")
                        variant = ProductVariant(
                            product_id=product.id,
                            company_id=current_user.company_id,
                            name=variant_name,
                        )
                        db.add(variant)
                        await db.flush()
                        _apply_variant_import_values(variant, row)
                        row_variant_created = True

            processed += 1
            products_created += int(row_product_created)
            if row_product_updated:
                products_updated.add(row_product_updated)
            variants_created += int(row_variant_created)
            if row_variant_updated:
                variants_updated.add(row_variant_updated)
        except Exception as exc:
            errors.append(f"Fila {index + 2}: {exc}")

    try:
        await db.commit()
    except Exception as exc:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Importación falló: {exc}") from exc

    return {
        "success": True,
        "count": processed,
        "products_created": products_created,
        "products_updated": len(products_updated),
        "variants_created": variants_created,
        "variants_updated": len(variants_updated),
        "errors": errors,
    }
