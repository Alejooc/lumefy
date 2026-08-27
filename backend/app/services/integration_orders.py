"""Order import/export services for installable integrations."""

from __future__ import annotations

from datetime import datetime
import hashlib
import json
from typing import Any
from urllib.parse import quote
import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.branch import Branch
from app.models.client import Client
from app.models.integration import IntegrationOrderLink, IntegrationRecordLink, IntegrationSource, IntegrationSyncRun
from app.models.product import Product
from app.models.product_variant import ProductVariant
from app.models.sale import Sale, SaleItem, SaleStatus
from app.models.user import User
from app.models.warehouse import Warehouse
from app.services.integration_service import (
    IntegrationRequestError,
    _as_float,
    _as_text,
    _endpoint_config,
    _fetch_entity,
    _request_json,
    _build_headers,
    _url_for,
    _value,
)


DEFAULT_ORDER_MAPPING: dict[str, str] = {
    "id": "id",
    "number": "invoice",
    "tracking": "track",
    "status": "state",
    "total": "total",
    "created_at": "created",
    "customer_name": "client_name",
    "items": "items",
    "item_sku": "sku",
    "item_quantity": "qty",
    "item_unit_price": "unit_price",
    "item_total": "line_total",
}


def _order_mapping(source: IntegrationSource) -> dict[str, Any]:
    configured = (source.configuration or {}).get("order_mapping") or {}
    return {**DEFAULT_ORDER_MAPPING, **configured} if isinstance(configured, dict) else DEFAULT_ORDER_MAPPING


def _mapped_order(value: Any, mapping: dict[str, Any], key: str, *fallbacks: str) -> Any:
    path = mapping.get(key)
    if isinstance(path, dict):
        path = path.get("path")
    result = _value(value, path) if isinstance(path, str) and path else None
    if result not in (None, ""):
        return result
    for fallback in fallbacks:
        result = _value(value, fallback)
        if result not in (None, ""):
            return result
    return None


def _safe_order_payload(source: IntegrationSource, order: dict[str, Any]) -> dict[str, Any]:
    """Keep an auditable, bounded order snapshot without storing credentials."""

    mapping = _order_mapping(source)
    items = _mapped_order(order, mapping, "items", "items")
    safe_items: list[dict[str, Any]] = []
    if isinstance(items, list):
        for item in items[:500]:
            if not isinstance(item, dict):
                continue
            safe_items.append(
                {
                    "sku": _as_text(_mapped_order(item, mapping, "item_sku", "sku", "code", "reference")),
                    "quantity": _as_float(_mapped_order(item, mapping, "item_quantity", "qty", "quantity")),
                    "unit_price": _as_float(_mapped_order(item, mapping, "item_unit_price", "unit_price", "price")),
                    "total": _as_float(_mapped_order(item, mapping, "item_total", "line_total", "total")),
                    "name": _as_text(_mapped_order(item, mapping, "item_name", "product_name", "name", "title")),
                }
            )
    return {
        "id": _as_text(_mapped_order(order, mapping, "id", "id", "order_id")),
        "number": _as_text(_mapped_order(order, mapping, "number", "invoice", "number", "order_number")),
        "tracking": _as_text(_mapped_order(order, mapping, "tracking", "track", "tracking")),
        "status": _as_text(_mapped_order(order, mapping, "status", "state", "status")),
        "total": _as_float(_mapped_order(order, mapping, "total", "total", "grand_total")),
        "created_at": _as_text(_mapped_order(order, mapping, "created_at", "created", "created_at")),
        "customer_name": _as_text(_mapped_order(order, mapping, "customer_name", "client_name", "customer_name")),
        "items": safe_items,
    }


def _payload_hash(payload: dict[str, Any]) -> str:
    canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


async def _fetch_order_detail(
    source: IntegrationSource,
    summary: dict[str, Any],
) -> dict[str, Any]:
    mapping = _order_mapping(source)
    external_id = _as_text(_mapped_order(summary, mapping, "id", "id", "order_id"))
    if not external_id:
        return summary
    if isinstance(_mapped_order(summary, mapping, "items", "items"), list):
        return summary

    endpoint = _endpoint_config(source, "orders")
    detail_path = endpoint.get("detail_path")
    if not detail_path:
        return summary
    path = str(detail_path).replace("{id}", quote(external_id, safe=""))
    status_code, payload = await _request_json(_url_for(source, path), _build_headers(source))
    detail_payload = _value(payload, endpoint.get("detail_data_path"), payload)
    if not isinstance(detail_payload, dict):
        raise IntegrationRequestError("El detalle de la orden no devolvió un objeto válido.", status_code)
    return detail_payload


async def _find_order_link(
    db: AsyncSession,
    source: IntegrationSource,
    external_order_id: str,
) -> IntegrationOrderLink | None:
    return await db.scalar(
        select(IntegrationOrderLink).where(
            IntegrationOrderLink.source_id == source.id,
            IntegrationOrderLink.external_order_id == external_order_id,
        )
    )


async def _resolve_order_line(
    db: AsyncSession,
    source: IntegrationSource,
    item: dict[str, Any],
    mapping: dict[str, Any],
) -> tuple[Product | None, ProductVariant | None]:
    sku = _as_text(_mapped_order(item, mapping, "item_sku", "sku", "code", "reference"))
    external_id = _as_text(_mapped_order(item, mapping, "item_external_id", "id", "product_id", "variant_id"))
    link = None
    if sku:
        link = await db.scalar(
            select(IntegrationRecordLink)
            .where(
                IntegrationRecordLink.source_id == source.id,
                IntegrationRecordLink.entity_type.in_(["product", "variant"]),
                IntegrationRecordLink.external_sku == sku,
            )
            .order_by(IntegrationRecordLink.updated_at.desc())
            .limit(1)
        )
    if link is None and external_id:
        link = await db.scalar(
            select(IntegrationRecordLink).where(
                IntegrationRecordLink.source_id == source.id,
                IntegrationRecordLink.entity_type.in_(["product", "variant"]),
                IntegrationRecordLink.external_id == external_id,
            )
        )
    if link:
        product = await db.get(Product, link.local_product_id) if link.local_product_id else None
        variant = await db.get(ProductVariant, link.local_variant_id) if link.local_variant_id else None
        if product and product.company_id == source.company_id:
            return product, variant if variant and variant.company_id == source.company_id else None

    if sku:
        variant = await db.scalar(
            select(ProductVariant)
            .join(Product, Product.id == ProductVariant.product_id)
            .where(ProductVariant.company_id == source.company_id, ProductVariant.sku == sku)
            .limit(1)
        )
        if variant:
            product = await db.get(Product, variant.product_id)
            return product, variant
        product = await db.scalar(
            select(Product).where(Product.company_id == source.company_id, Product.sku == sku).limit(1)
        )
        if product:
            return product, None
    return None, None


async def _resolve_fulfillment_context(
    db: AsyncSession,
    source: IntegrationSource,
) -> tuple[Branch | None, Warehouse | None, User | None]:
    configuration = source.configuration or {}
    orders_config = configuration.get("orders") or {}
    branch_id = orders_config.get("branch_id") or configuration.get("inventory_branch_id")
    warehouse_id = orders_config.get("warehouse_id") or configuration.get("inventory_warehouse_id")

    branch_query = select(Branch).where(Branch.company_id == source.company_id, Branch.is_active.is_(True))
    if branch_id:
        try:
            branch_query = branch_query.where(Branch.id == uuid.UUID(str(branch_id)))
        except ValueError:
            return None, None, None
    branch = (await db.execute(branch_query.order_by(Branch.created_at.asc()).limit(1))).scalars().first()
    if not branch:
        return None, None, None

    warehouse_query = select(Warehouse).where(Warehouse.branch_id == branch.id, Warehouse.is_active.is_(True))
    if warehouse_id:
        try:
            warehouse_query = warehouse_query.where(Warehouse.id == uuid.UUID(str(warehouse_id)))
        except ValueError:
            return branch, None, None
    else:
        warehouse_query = warehouse_query.order_by(Warehouse.is_default.desc(), Warehouse.created_at.asc())
    warehouse = (await db.execute(warehouse_query.limit(1))).scalars().first()
    user = await db.scalar(
        select(User)
        .where(User.company_id == source.company_id, User.is_active.is_(True))
        .order_by(User.created_at.asc())
        .limit(1)
    )
    return branch, warehouse, user


async def _find_or_create_client(
    db: AsyncSession,
    source: IntegrationSource,
    customer_name: str | None,
) -> Client | None:
    if not customer_name:
        return None
    client = await db.scalar(
        select(Client).where(
            Client.company_id == source.company_id,
            func.lower(func.trim(Client.name)) == customer_name.casefold(),
        ).limit(1)
    )
    if client:
        return client
    client = Client(
        id=uuid.uuid4(),
        company_id=source.company_id,
        name=customer_name[:120],
        status="active",
        notes="Cliente importado desde ElegantHome; la API solo entregó el nombre.",
    )
    db.add(client)
    await db.flush()
    return client


async def _create_imported_sale(
    db: AsyncSession,
    source: IntegrationSource,
    order: dict[str, Any],
    branch: Branch,
    warehouse: Warehouse,
    user: User,
) -> Sale:
    mapping = _order_mapping(source)
    items_value = _mapped_order(order, mapping, "items", "items")
    if not isinstance(items_value, list) or not items_value:
        raise IntegrationRequestError("La orden externa no contiene líneas de productos.", 422)

    resolved_items: list[tuple[dict[str, Any], Product, ProductVariant | None, float, float]] = []
    for raw_item in items_value[:500]:
        if not isinstance(raw_item, dict):
            continue
        product, variant = await _resolve_order_line(db, source, raw_item, mapping)
        sku = _as_text(_mapped_order(raw_item, mapping, "item_sku", "sku", "code", "reference"))
        if not product:
            raise IntegrationRequestError(f"No hay homologación local para el SKU {sku or 'sin SKU'}.", 422)
        quantity = _as_float(_mapped_order(raw_item, mapping, "item_quantity", "qty", "quantity")) or 0
        unit_price = _as_float(_mapped_order(raw_item, mapping, "item_unit_price", "unit_price", "price")) or 0
        line_total = _as_float(_mapped_order(raw_item, mapping, "item_total", "line_total", "total"))
        if quantity <= 0:
            raise IntegrationRequestError(f"La cantidad del SKU {sku or 'sin SKU'} no es válida.", 422)
        resolved_items.append((raw_item, product, variant, quantity, line_total if line_total is not None else unit_price * quantity))

    if not resolved_items:
        raise IntegrationRequestError("La orden externa no contiene líneas utilizables.", 422)

    customer_name = _as_text(_mapped_order(order, mapping, "customer_name", "client_name", "customer_name"))
    client = await _find_or_create_client(db, source, customer_name)
    external_number = _as_text(_mapped_order(order, mapping, "number", "invoice", "number", "order_number"))
    external_id = _as_text(_mapped_order(order, mapping, "id", "id", "order_id")) or ""
    total_from_provider = _as_float(_mapped_order(order, mapping, "total", "total", "grand_total"))
    subtotal = sum(line_total for _, _, _, _, line_total in resolved_items)
    total = total_from_provider if total_from_provider is not None else subtotal
    sale = Sale(
        id=uuid.uuid4(),
        company_id=source.company_id,
        branch_id=branch.id,
        warehouse_id=warehouse.id,
        user_id=user.id,
        client_id=client.id if client else None,
        status=SaleStatus.DRAFT,
        origin_channel="EXTERNAL_APP",
        integration_source_id=source.id,
        payment_method="EXTERNAL_ELEGANTHOME",
        subtotal=subtotal,
        tax=0.0,
        discount=0.0,
        shipping_cost=0.0,
        total=total,
        notes=(f"Importada de ElegantHome · {external_number or external_id}")[:500],
    )
    db.add(sale)
    await db.flush()
    for _, product, variant, quantity, line_total in resolved_items:
        unit_price = line_total / quantity if quantity else 0
        db.add(
            SaleItem(
                id=uuid.uuid4(),
                company_id=source.company_id,
                sale_id=sale.id,
                product_id=product.id,
                variant_id=variant.id if variant else None,
                quantity=quantity,
                price=unit_price,
                discount=0.0,
                total=line_total,
            )
        )
    await db.flush()
    return sale


async def sync_external_orders(
    db: AsyncSession,
    source: IntegrationSource,
    run: IntegrationSyncRun,
    progress_callback: Any = None,
) -> None:
    """Pull ElegantHome orders, import mapped orders and keep unmapped ones pending."""

    from app.services.integration_service import _report_progress

    orders = await _fetch_entity(source, "orders", progress_callback)
    branch, warehouse, user = await _resolve_fulfillment_context(db, source)
    processed = created = pending = skipped = failed = 0
    mapping = _order_mapping(source)
    await _report_progress(
        progress_callback,
        stage="PROCESSING",
        message=f"Procesando órdenes externas: 0 de {len(orders)}.",
        percent=45,
        current=0,
        total=len(orders),
        entity="orders",
        items_received=len(orders),
    )

    for index, summary in enumerate(orders, start=1):
        processed += 1
        try:
            order = await _fetch_order_detail(source, summary)
            safe_payload = _safe_order_payload(source, order)
            external_id = _as_text(_mapped_order(order, mapping, "id", "id", "order_id"))
            if not external_id:
                raise IntegrationRequestError("La orden externa no tiene identificador.", 422)
            link = await _find_order_link(db, source, external_id)
            if link and link.status == "IMPORTED" and link.sale_id:
                skipped += 1
                await _report_progress(
                    progress_callback,
                    stage="PROCESSING",
                    message=f"Orden {external_id} ya importada; se omite.",
                    percent=45 + int(50 * index / max(1, len(orders))),
                    current=index,
                    total=len(orders),
                    entity="orders",
                    items_received=len(orders),
                    items_total=len(orders),
                    created=created,
                    items_failed=pending + failed,
                )
                continue
            if not branch or not warehouse or not user:
                raise IntegrationRequestError("Configura una sucursal, bodega y usuario activos antes de importar órdenes.", 422)
            sale = await _create_imported_sale(db, source, order, branch, warehouse, user)
            if link is None:
                link = IntegrationOrderLink(
                    id=uuid.uuid4(),
                    company_id=source.company_id,
                    source_id=source.id,
                    external_order_id=external_id,
                )
                db.add(link)
            link.sale_id = sale.id
            link.external_number = _as_text(_mapped_order(order, mapping, "number", "invoice", "number"))
            link.direction = "INBOUND"
            link.status = "IMPORTED"
            link.provider_status = _as_text(_mapped_order(order, mapping, "status", "state", "status"))
            link.payload_hash = _payload_hash(safe_payload)
            link.raw_payload = safe_payload
            link.error_message = None
            link.imported_at = datetime.utcnow()
            created += 1
        except IntegrationRequestError as exc:
            safe_payload = _safe_order_payload(source, summary)
            external_id = _as_text(_mapped_order(summary, mapping, "id", "id", "order_id")) or f"unknown-{index}"
            link = await _find_order_link(db, source, external_id)
            if link is None:
                link = IntegrationOrderLink(
                    id=uuid.uuid4(),
                    company_id=source.company_id,
                    source_id=source.id,
                    external_order_id=external_id,
                )
                db.add(link)
            link.external_number = _as_text(_mapped_order(summary, mapping, "number", "invoice", "number"))
            link.direction = "INBOUND"
            link.status = "PENDING_MAPPING"
            link.provider_status = _as_text(_mapped_order(summary, mapping, "status", "state", "status"))
            link.payload_hash = _payload_hash(safe_payload)
            link.raw_payload = safe_payload
            link.error_message = str(exc)[:1000]
            pending += 1
        except Exception as exc:  # noqa: BLE001 - one bad order must not abort the batch
            failed += 1
            run.details = {
                **(run.details or {}),
                "last_order_error": str(exc)[:1000],
            }
        if index % 10 == 0 or index == len(orders):
            await db.flush()
            await _report_progress(
                progress_callback,
                stage="PROCESSING",
                message=f"Procesando órdenes externas: {index} de {len(orders)}.",
                percent=45 + int(50 * index / max(1, len(orders))),
                current=index,
                total=len(orders),
                entity="orders",
                items_received=len(orders),
                items_total=len(orders),
                created=created,
                items_failed=pending + failed,
            )

    run.items_failed = pending + failed
    run.details = {
        **(run.details or {}),
        "orders_processed": processed,
        "orders_created": created,
        "orders_pending_mapping": pending,
        "orders_skipped": skipped,
        "orders_failed": failed,
    }


async def export_sale_to_source(
    db: AsyncSession,
    source: IntegrationSource,
    sale: Sale,
) -> IntegrationOrderLink:
    """Create one order in ElegantHome from a local sale."""

    existing = await db.scalar(
        select(IntegrationOrderLink).where(
            IntegrationOrderLink.source_id == source.id,
            IntegrationOrderLink.sale_id == sale.id,
            IntegrationOrderLink.direction == "OUTBOUND",
            IntegrationOrderLink.status == "EXPORTED",
        ).limit(1)
    )
    if existing:
        return existing

    configuration = source.configuration or {}
    orders_config = configuration.get("orders") or {}
    export_config = orders_config.get("export") or {}
    client_name = sale.client.name if sale.client else "Consumidor final"
    name_parts = client_name.split(maxsplit=1)
    address = sale.client.address if sale.client and sale.client.address else sale.shipping_address
    state = export_config.get("state")
    city = export_config.get("city")
    if not address or state in (None, "") or city in (None, ""):
        raise IntegrationRequestError(
            "Para crear la orden externa configura dirección, estado y ciudad de entrega en la conexión ElegantHome.",
            422,
        )
    items: list[dict[str, Any]] = []
    for item in sale.items:
        sku = item.variant.sku if item.variant and item.variant.sku else item.product.sku if item.product else None
        if not sku:
            raise IntegrationRequestError("Todos los productos de la venta deben tener SKU para exportar la orden.", 422)
        items.append({"sku": sku, "qty": item.quantity})
    if not items:
        raise IntegrationRequestError("La venta no tiene líneas para exportar.", 422)

    body = {
        "client": {
            "idclient": 0,
            "docid": sale.client.tax_id if sale.client else None,
            "name": name_parts[0],
            "lastname": name_parts[1] if len(name_parts) > 1 else "Cliente",
            "phone": sale.client.phone if sale.client and sale.client.phone else "0000000000",
            "email": sale.client.email if sale.client else None,
        },
        "address": {
            "idaddress": 0,
            "address": address,
            "state": state,
            "city": city,
            "nbh": export_config.get("neighborhood") or "",
        },
        "payment_method": export_config.get("payment_method", 1),
        "delivery": float(sale.shipping_cost or 0),
        "notes": sale.notes or "Orden creada desde Lumefy",
        "items": items,
    }
    endpoint = _endpoint_config(source, "orders")
    path = endpoint.get("create_path") or endpoint.get("path") or "/api/external/orders"
    status_code, payload = await _request_json(
        _url_for(source, str(path)),
        _build_headers(source),
        method="POST",
        json_body=body,
    )
    if not isinstance(payload, dict) or payload.get("tipo") not in (1, "1", True):
        message = payload.get("msg") if isinstance(payload, dict) else None
        raise IntegrationRequestError(str(message or "ElegantHome rechazó la creación de la orden."), status_code)
    data = payload.get("data") if isinstance(payload.get("data"), dict) else {}
    external_id = _as_text(data.get("order_id") or data.get("id"))
    if not external_id:
        raise IntegrationRequestError("ElegantHome creó la orden pero no devolvió su identificador.", status_code)
    link = IntegrationOrderLink(
        id=uuid.uuid4(),
        company_id=source.company_id,
        source_id=source.id,
        sale_id=sale.id,
        external_order_id=external_id,
        external_number=_as_text(data.get("invoice")),
        direction="OUTBOUND",
        status="EXPORTED",
        provider_status="CREATED",
        payload_hash=_payload_hash({"sale_id": str(sale.id), "items": items}),
        raw_payload={
            "external_order_id": external_id,
            "external_number": _as_text(data.get("invoice")),
            "total": _as_float(data.get("total")),
            "items": len(items),
        },
        imported_at=datetime.utcnow(),
    )
    db.add(link)
    await db.flush()
    return link
