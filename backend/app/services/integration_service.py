from __future__ import annotations

import asyncio
import base64
import ipaddress
import json
import socket
import uuid
from datetime import datetime
from typing import Any
from urllib import error as urlerror
from urllib import parse as urlparse
from urllib import request as urlrequest

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.branch import Branch
from app.models.category import Category
from app.models.integration import IntegrationRecordLink, IntegrationSource, IntegrationSyncRun
from app.models.inventory import Inventory
from app.models.product import Product
from app.models.product_image import ProductImage
from app.models.product_variant import ProductVariant
from app.models.warehouse import Warehouse


class IntegrationRequestError(Exception):
    def __init__(self, message: str, status_code: int | None = None):
        super().__init__(message)
        self.status_code = status_code


class IntegrationSyncConflict(Exception):
    """Raised when an equivalent sync is already queued or running."""


def validate_source(source: IntegrationSource) -> None:
    if source.source_type.upper() != "REST":
        raise IntegrationRequestError("El primer conector soportado es REST.")
    _validate_outbound_url(source.base_url)


def _validate_url_syntax(url: str) -> urlparse.SplitResult:
    parsed = urlparse.urlsplit(url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise IntegrationRequestError("La URL debe usar http:// o https:// y contener un host válido.")
    if parsed.username or parsed.password:
        raise IntegrationRequestError("La URL no puede incluir usuario ni contraseña.")
    return parsed


def _validate_outbound_url(url: str) -> None:
    parsed = _validate_url_syntax(url)
    if settings.INTEGRATION_ALLOW_PRIVATE_NETWORKS:
        return
    try:
        addresses = socket.getaddrinfo(
            parsed.hostname,
            parsed.port or (443 if parsed.scheme == "https" else 80),
            type=socket.SOCK_STREAM,
        )
    except socket.gaierror as exc:
        raise IntegrationRequestError("No se pudo resolver el host del origen de datos.") from exc
    if not addresses:
        raise IntegrationRequestError("El host del origen de datos no resolvió ninguna dirección.")
    for address in addresses:
        raw_ip = str(address[4][0]).split("%", 1)[0]
        try:
            resolved_ip = ipaddress.ip_address(raw_ip)
        except ValueError as exc:
            raise IntegrationRequestError("El host resolvió una dirección no válida.") from exc
        if not resolved_ip.is_global:
            raise IntegrationRequestError(
                "Por seguridad, el origen no puede apuntar a localhost ni a una red privada o reservada."
            )


def _origin(parsed: urlparse.SplitResult) -> tuple[str, str, int]:
    default_port = 443 if parsed.scheme == "https" else 80
    return parsed.scheme, str(parsed.hostname).lower(), parsed.port or default_port


def _url_for(source: IntegrationSource, path: str | None) -> str:
    base = _validate_url_syntax(source.base_url)
    url = urlparse.urljoin(source.base_url.rstrip("/") + "/", (path or "").lstrip("/"))
    target = _validate_url_syntax(url)
    if _origin(base) != _origin(target):
        raise IntegrationRequestError("Los endpoints deben permanecer en el mismo host que la URL base.")
    return url


def _url_with_query(url: str, params: dict[str, Any]) -> str:
    """Add or replace query parameters while preserving existing endpoint parameters."""
    parsed = urlparse.urlsplit(url)
    query = dict(urlparse.parse_qsl(parsed.query, keep_blank_values=True))
    query.update({str(key): str(value) for key, value in params.items() if key and value is not None})
    return urlparse.urlunsplit(
        (parsed.scheme, parsed.netloc, parsed.path, urlparse.urlencode(query), parsed.fragment)
    )


def _build_headers(source: IntegrationSource) -> dict[str, str]:
    credentials = source.credentials or {}
    configuration = source.configuration or {}
    headers = {
        "Accept": "application/json",
        "User-Agent": "Lumefy-Integration/1.0",
    }
    auth_type = (source.auth_type or "none").lower()
    if auth_type == "bearer":
        token = credentials.get("token") or credentials.get("access_token")
        if token:
            headers["Authorization"] = f"Bearer {token}"
    elif auth_type in {"api_key", "apikey"}:
        api_key = credentials.get("api_key") or credentials.get("token")
        header_name = configuration.get("api_key_header") or "X-API-Key"
        if api_key:
            headers[str(header_name)] = str(api_key)
    elif auth_type == "custom_headers":
        custom_headers = credentials.get("headers") or {}
        if isinstance(custom_headers, dict):
            headers.update({str(key): str(value) for key, value in custom_headers.items()})
    elif auth_type == "basic":
        username = str(credentials.get("username") or "")
        password = str(credentials.get("password") or "")
        encoded = base64.b64encode(f"{username}:{password}".encode("utf-8")).decode("ascii")
        headers["Authorization"] = f"Basic {encoded}"
    return headers


class _SafeRedirectHandler(urlrequest.HTTPRedirectHandler):
    def __init__(self, allowed_origin: tuple[str, str, int]):
        super().__init__()
        self.allowed_origin = allowed_origin

    def redirect_request(self, req: Any, fp: Any, code: int, msg: str, headers: Any, newurl: str) -> Any:
        _validate_outbound_url(newurl)
        if _origin(_validate_url_syntax(newurl)) != self.allowed_origin:
            raise IntegrationRequestError("La API intentó redirigir la petición a otro host.")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def _request_json_sync(url: str, headers: dict[str, str]) -> tuple[int, Any]:
    _validate_outbound_url(url)
    request = urlrequest.Request(url, headers=headers, method="GET")
    try:
        opener = urlrequest.build_opener(_SafeRedirectHandler(_origin(_validate_url_syntax(url))))
        with opener.open(request, timeout=settings.INTEGRATION_REQUEST_TIMEOUT_SECONDS) as response:
            status_code = int(response.getcode())
            body = response.read().decode("utf-8")
            try:
                return status_code, json.loads(body) if body else {}
            except json.JSONDecodeError as exc:
                raise IntegrationRequestError("La respuesta de la API no es JSON válido.", status_code) from exc
    except urlerror.HTTPError as exc:
        try:
            detail = exc.read().decode("utf-8")[:500]
        except Exception:
            detail = ""
        raise IntegrationRequestError(f"La API respondió HTTP {exc.code}. {detail}".strip(), exc.code) from exc
    except (urlerror.URLError, TimeoutError) as exc:
        raise IntegrationRequestError(f"No se pudo conectar con la API: {exc}") from exc


async def _request_json(url: str, headers: dict[str, str]) -> tuple[int, Any]:
    return await asyncio.to_thread(_request_json_sync, url, headers)


def _value(payload: Any, path: str | None, default: Any = None) -> Any:
    if path in (None, "", "."):
        return payload
    current = payload
    for part in str(path).removeprefix("$.").split("."):
        if part.endswith("[]"):
            part = part[:-2]
        if isinstance(current, dict):
            current = current.get(part, default)
        elif isinstance(current, list) and part.isdigit() and int(part) < len(current):
            current = current[int(part)]
        else:
            return default
        if current is default:
            return default
    return current


def _as_float(value: Any, default: float | None = None) -> float | None:
    if value in (None, ""):
        return default
    try:
        return float(str(value).replace(",", "."))
    except (TypeError, ValueError):
        return default


def _endpoint_config(source: IntegrationSource, entity: str) -> dict[str, Any]:
    configuration = source.configuration or {}
    endpoints = configuration.get("endpoints") or {}
    endpoint = endpoints.get(entity) or configuration.get(f"{entity}_endpoint") or {}
    if isinstance(endpoint, str):
        return {"path": endpoint}
    return endpoint if isinstance(endpoint, dict) else {}


def _extract_entity_rows(payload: Any, endpoint: dict[str, Any], entity: str, status_code: int) -> list[dict[str, Any]]:
    data = _value(payload, endpoint.get("data_path"), payload)
    if isinstance(data, dict):
        data = data.get("items") or data.get("results") or data.get("data") or []
        if not data and entity == "products" and any(
            key in payload for key in ("product_id", "product_name", "name", "title", "variants")
        ):
            data = [payload]
    if not isinstance(data, list):
        raise IntegrationRequestError(f"El endpoint de {entity} no devolvió una lista de registros.", status_code)
    return [item for item in data if isinstance(item, dict)]


def _pagination_config(endpoint: dict[str, Any]) -> dict[str, Any]:
    pagination = endpoint.get("pagination") or {}
    return pagination if isinstance(pagination, dict) else {}


def _field_map(source: IntegrationSource) -> dict[str, Any]:
    return (source.configuration or {}).get("field_map") or {}


def _mapped(item: dict[str, Any], mapping: dict[str, Any], key: str, *fallbacks: str) -> Any:
    path = mapping.get(key)
    if isinstance(path, dict):
        path = path.get("path")
    value = _value(item, path) if isinstance(path, str) and path else None
    if value not in (None, ""):
        return value
    for fallback in fallbacks:
        value = _value(item, fallback)
        if value not in (None, ""):
            return value
    return None


def _normal_key(value: Any) -> str:
    return "".join(char for char in str(value).lower() if char.isalnum())


def _path_candidates(payload: Any, aliases: tuple[str, ...], prefix: str = "") -> list[tuple[str, int]]:
    if not isinstance(payload, dict):
        return []
    normalized_aliases = {_normal_key(alias) for alias in aliases}
    candidates: list[tuple[str, int]] = []
    for key, value in payload.items():
        path = f"{prefix}.{key}" if prefix else str(key)
        key_normalized = _normal_key(key)
        score = 0
        if key_normalized in normalized_aliases:
            score = 100
        elif any(alias and alias in key_normalized for alias in normalized_aliases):
            score = 75
        if score:
            candidates.append((path, score))
        if isinstance(value, dict) and prefix.count(".") < 1:
            candidates.extend(_path_candidates(value, aliases, path))
    return sorted(candidates, key=lambda candidate: (-candidate[1], candidate[0]))


def _list_key(payload: Any, aliases: tuple[str, ...]) -> str | None:
    if not isinstance(payload, dict):
        return None
    normalized_aliases = {_normal_key(alias) for alias in aliases}
    for key, value in payload.items():
        if isinstance(value, list) and _normal_key(key) in normalized_aliases:
            return str(key)
    return None


def _paths_in_payload(payload: Any, prefix: str = "") -> list[str]:
    paths: list[str] = []
    if isinstance(payload, dict):
        for key, value in payload.items():
            path = f"{prefix}.{key}" if prefix else str(key)
            paths.append(path)
            paths.extend(_paths_in_payload(value, path))
    elif isinstance(payload, list):
        array_path = f"{prefix}[]" if prefix else "[]"
        paths.append(array_path)
        if payload and isinstance(payload[0], dict):
            paths.extend(_paths_in_payload(payload[0], array_path))
    return paths


def _suggestion(
    canonical: str,
    candidates: list[tuple[str, int]],
    *,
    required: bool = False,
    kind: str = "scalar",
    reason: str | None = None,
) -> tuple[dict[str, Any], str | None]:
    paths = [path for path, _ in candidates]
    source_path = candidates[0][0] if candidates else None
    confidence = candidates[0][1] if candidates else 0
    if source_path and "[]" in source_path:
        confidence = min(confidence, 95)
    return (
        {
            "canonical": canonical,
            "source_path": source_path,
            "confidence": confidence,
            "required": required,
            "kind": kind,
            "reason": reason,
            "candidates": paths[:5],
        },
        source_path,
    )


def _suggest_mapping_from_sample(sample: dict[str, Any]) -> dict[str, Any]:
    mapping: dict[str, Any] = {}
    suggestions: list[dict[str, Any]] = []

    def add(canonical: str, aliases: tuple[str, ...], **kwargs: Any) -> None:
        suggestion, source_path = _suggestion(canonical, _path_candidates(sample, aliases), **kwargs)
        suggestions.append(suggestion)
        if source_path:
            mapping[canonical] = source_path

    add("product.external_id", ("product_id", "external_id", "id", "uuid"), required=True)
    add("product.name", ("product_name", "name", "title"), required=True)
    add("product.description", ("description", "body", "body_html"))
    add("product.sku", ("product_sku", "sku", "reference", "code"))
    add("product.barcode", ("barcode", "ean", "upc", "gtin"))
    add("product.price", ("sale_price", "selling_price", "price"))
    add("product.cost", ("purchase_price", "cost"))
    add("product.category.external_id", ("category_id",))
    add("product.category.name", ("category_name",))
    add("product.supplier.external_id", ("provider_id", "supplier_id", "vendor_id"))
    add("product.supplier.name", ("provider_name", "supplier_name", "vendor_name"))
    add("product.attributes.material", ("material",))

    images_key = _list_key(sample, ("images", "pictures", "photos", "media"))
    if images_key:
        suggestion, _ = _suggestion(
            "product.images", [(f"{images_key}[]", 95)], kind="collection", reason="Lista de imágenes del producto."
        )
        suggestions.append(suggestion)
        mapping["product.images"] = f"{images_key}[]"

    product_attribute_paths: list[str] = []
    for aliases, label in [(("specs", "specifications"), "Especificaciones"), (("props", "properties"), "Propiedades")]:
        key = _list_key(sample, aliases)
        if key:
            path = f"{key}[]"
            product_attribute_paths.append(path)
            suggestion, _ = _suggestion(
                f"product.attributes.{key}", [(path, 90)], kind="attributes", reason=f"{label} en formato clave/valor."
            )
            suggestions.append(suggestion)
            mapping[f"product.attributes.{key}"] = path

    variants_key = _list_key(sample, ("variants", "variations", "options", "skus"))
    variant_attribute_key = None
    if variants_key:
        variants = sample.get(variants_key) or []
        first_variant = variants[0] if variants and isinstance(variants[0], dict) else {}
        prefix = f"{variants_key}[]"

        def add_variant(canonical: str, aliases: tuple[str, ...], **kwargs: Any) -> None:
            candidates = [(f"{prefix}.{path}", score) for path, score in _path_candidates(first_variant, aliases)]
            suggestion, source_path = _suggestion(canonical, candidates, **kwargs)
            suggestions.append(suggestion)
            if source_path:
                mapping[canonical] = source_path

        add_variant("variant.external_id", ("variant_id", "external_id", "id", "uuid"), required=True)
        add_variant("variant.sku", ("sku", "code", "reference"), required=True)
        add_variant("variant.name", ("variant_name", "name", "title", "medida", "size", "color"), required=True)
        add_variant("variant.barcode", ("barcode", "ean", "upc", "gtin", "item_code"))
        add_variant("variant.price", ("price", "sale_price", "selling_price"))
        add_variant("variant.cost", ("cost", "purchase_price"))
        add_variant("variant.stock", ("stock", "quantity", "available", "inventory"))
        add_variant("variant.stock_temp", ("stock_temp", "temporary_stock", "reserved"))
        variant_attribute_key = _list_key(first_variant, ("properties", "attributes", "options"))
        if variant_attribute_key:
            path = f"{prefix}.{variant_attribute_key}[]"
            suggestion, _ = _suggestion(
                "variant.attributes", [(path, 90)], kind="attributes", reason="Atributos propios de la variante."
            )
            suggestions.append(suggestion)
            mapping["variant.attributes"] = path

    collections = {
        "variants_path": f"{variants_key}[]" if variants_key else None,
        "images_path": f"{images_key}[]" if images_key else None,
        "product_attribute_paths": product_attribute_paths,
        "variant_attributes_path": f"{variants_key}[].{variant_attribute_key}[]" if variants_key and variant_attribute_key else None,
    }
    detected_shape = "variants" if variants_key else "simple"
    warnings: list[str] = []
    if not mapping.get("product.external_id"):
        warnings.append("No se encontró un identificador externo claro para el producto.")
    if not mapping.get("product.name"):
        warnings.append("No se encontró un nombre claro para el producto.")
    if variants_key and not mapping.get("variant.sku"):
        warnings.append("Se detectaron variantes, pero no se encontró un SKU de variante.")
    if mapping.get("product.supplier.external_id") or mapping.get("product.supplier.name"):
        warnings.append("El proveedor se conservará como dato de relación; confirma si debe vincularse a un proveedor de Lumefy.")
    return {
        "mapping": mapping,
        "collections": collections,
        "suggestions": suggestions,
        "detected_paths": _paths_in_payload(sample),
        "detected_shape": detected_shape,
        "warnings": warnings,
    }


async def suggest_mapping_source(source: IntegrationSource) -> dict[str, Any]:
    validate_source(source)
    endpoint, request_url, pagination_enabled, page, page_size = _preview_request_details(source, "products")
    if not request_url:
        raise IntegrationRequestError("Configura primero el endpoint de productos.")
    status_code, payload = await _request_json(request_url, _build_headers(source))
    rows = _extract_entity_rows(payload, endpoint, "products", status_code)
    if not rows:
        raise IntegrationRequestError("La API respondió sin registros para detectar el mapeo.", status_code)
    suggestion = _suggest_mapping_from_sample(rows[0])
    return {
        "source_id": source.id,
        "success": True,
        "message": "Mapeo sugerido a partir de la primera muestra. Revísalo antes de confirmarlo.",
        "request_url": _safe_preview_url(request_url),
        "sample_count": len(rows),
        "catalog_mode": "auto",
        **suggestion,
    }


def _mapping_path(mapping: dict[str, Any], key: str) -> str | None:
    value = mapping.get(key)
    if isinstance(value, dict):
        value = value.get("path")
    return str(value) if isinstance(value, str) and value else None


def _mapped_context(
    item: dict[str, Any], mapping: dict[str, Any], key: str, collection_prefix: str, *fallbacks: str
) -> Any:
    path = _mapping_path(mapping, key)
    if path:
        prefix = collection_prefix.rstrip(".")
        if path.startswith(f"{prefix}."):
            path = path[len(prefix) + 1 :]
        elif path.startswith(f"{prefix}[]"):
            path = path[len(prefix) + 2 :].lstrip(".")
        value = _value(item, path)
        if value not in (None, ""):
            return value
    for fallback in fallbacks:
        value = _value(item, fallback)
        if value not in (None, ""):
            return value
    return None


def _as_list(value: Any) -> list[Any]:
    if isinstance(value, list):
        return value
    return []


def _attribute_pairs(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return {str(key): item for key, item in value.items() if item not in (None, "")}
    if not isinstance(value, list):
        return {}
    attributes: dict[str, Any] = {}
    for item in value:
        if not isinstance(item, dict):
            continue
        key = item.get("spec") or item.get("property") or item.get("name") or item.get("key")
        item_value = item.get("value")
        if item_value in (None, ""):
            item_value = item.get("custom_value")
        if key not in (None, "") and item_value not in (None, ""):
            attributes[str(key).strip()] = item_value
    return attributes


def _collect_product_attributes(item: dict[str, Any], mapping: dict[str, Any]) -> dict[str, Any]:
    attributes: dict[str, Any] = {}
    for canonical, path_value in mapping.items():
        if not canonical.startswith("product.attributes."):
            continue
        path = path_value.get("path") if isinstance(path_value, dict) else path_value
        raw = _value(item, path) if isinstance(path, str) else None
        key = canonical.removeprefix("product.attributes.")
        if isinstance(raw, (list, dict)):
            pairs = _attribute_pairs(raw)
            attributes.update(pairs or {key: raw})
        elif raw not in (None, ""):
            attributes[key] = raw
    return attributes


def _collect_variant_attributes(
    variant: dict[str, Any], mapping: dict[str, Any], collection_prefix: str
) -> dict[str, Any]:
    path = _mapping_path(mapping, "variant.attributes")
    if not path:
        return {}
    prefix = collection_prefix.rstrip(".")
    if path.startswith(f"{prefix}."):
        path = path[len(prefix) + 1 :]
    elif path.startswith(f"{prefix}[]"):
        path = path[len(prefix) + 2 :].lstrip(".")
    return _attribute_pairs(_value(variant, path))


def _asset_url(source: IntegrationSource, value: Any) -> str | None:
    if value in (None, ""):
        return None
    url = str(value).strip()
    if urlparse.urlparse(url).scheme in {"http", "https"}:
        return url
    configuration = source.configuration or {}
    base_url = str(configuration.get("asset_base_url") or source.base_url)
    return urlparse.urljoin(base_url.rstrip("/") + "/", url.lstrip("/"))


async def _sync_category(
    db: AsyncSession, source: IntegrationSource, name: str | None
) -> uuid.UUID | None:
    normalized = (name or "").strip()
    if not normalized:
        return None
    result = await db.execute(
        select(Category).where(
            Category.company_id == source.company_id,
            Category.is_active.is_(True),
            Category.name.ilike(normalized),
        ).limit(1)
    )
    category = result.scalars().first()
    if not category:
        category = Category(id=uuid.uuid4(), company_id=source.company_id, name=normalized)
        db.add(category)
        await db.flush()
    return category.id


async def _sync_product_images(
    db: AsyncSession, source: IntegrationSource, product: Product, item: dict[str, Any], mapping: dict[str, Any]
) -> None:
    path = _mapping_path(mapping, "product.images")
    if not path:
        path = (source.configuration or {}).get("collections", {}).get("images_path")
    image_items = _as_list(_value(item, path)) if path else []
    if not image_items:
        return
    first_url: str | None = None
    for index, image in enumerate(image_items):
        if isinstance(image, str):
            image_url = _asset_url(source, image)
            order = index
        elif isinstance(image, dict):
            image_url = _asset_url(source, image.get("url") or image.get("image_url") or image.get("src"))
            try:
                order = int(image.get("order") or image.get("position") or index)
            except (TypeError, ValueError):
                order = index
        else:
            continue
        if not image_url:
            continue
        first_url = first_url or image_url
        existing = (await db.execute(
            select(ProductImage).where(ProductImage.product_id == product.id, ProductImage.image_url == image_url).limit(1)
        )).scalars().first()
        if existing:
            existing.order = order
        else:
            db.add(ProductImage(id=uuid.uuid4(), product_id=product.id, image_url=image_url, order=order))
    if first_url:
        product.image_url = first_url


def _safe_preview_url(url: str) -> str:
    sensitive_markers = ("token", "key", "secret", "password", "authorization", "auth")
    parsed = urlparse.urlsplit(url)
    query = []
    for key, value in urlparse.parse_qsl(parsed.query, keep_blank_values=True):
        safe_value = "***" if any(marker in key.lower() for marker in sensitive_markers) else value
        query.append((key, safe_value))
    return urlparse.urlunsplit(
        (parsed.scheme, parsed.netloc, parsed.path, urlparse.urlencode(query), parsed.fragment)
    )


def _preview_request_details(
    source: IntegrationSource, entity: str
) -> tuple[dict[str, Any], str | None, bool, int | None, int | None]:
    endpoint = _endpoint_config(source, entity)
    path = endpoint.get("path")
    if not path:
        return endpoint, None, False, None, None

    url = _url_for(source, str(path))
    pagination = _pagination_config(endpoint)
    if not pagination.get("enabled", False):
        return endpoint, url, False, None, None
    if str(pagination.get("type", "page")).lower() != "page":
        raise IntegrationRequestError("La paginación configurada debe usar el tipo 'page'.")
    try:
        page = max(1, int(pagination.get("start_page") or 1))
        per_page = max(1, int(pagination.get("per_page") or 50))
    except (TypeError, ValueError) as exc:
        raise IntegrationRequestError("La configuración de paginación debe usar números válidos.") from exc
    request_url = _url_with_query(
        url,
        {
            str(pagination.get("page_param") or "page"): page,
            str(pagination.get("per_page_param") or "per_page"): per_page,
        },
    )
    return endpoint, request_url, True, page, per_page


def _preview_mapped_item(item: dict[str, Any], mapping: dict[str, Any], entity: str) -> dict[str, Any]:
    if entity == "products":
        return {
            "external_id": _mapped(item, mapping, "product.external_id", "id", "external_id", "uuid", "product_id"),
            "name": _mapped(item, mapping, "product.name", "name", "title", "product_name"),
            "sku": _mapped(item, mapping, "product.sku", "sku", "code", "reference"),
            "price": _as_float(_mapped(item, mapping, "product.price", "price", "sale_price")),
            "cost": _as_float(_mapped(item, mapping, "product.cost", "cost", "purchase_price")),
        }
    return {
        "external_id": _mapped(item, mapping, "inventory.external_id", "product_id", "id", "sku"),
        "sku": _mapped(item, mapping, "inventory.sku", "sku", "product_sku"),
        "quantity": _as_float(_mapped(item, mapping, "inventory.quantity", "quantity", "stock", "available")),
    }


async def _preview_entity(source: IntegrationSource, entity: str, sample_limit: int = 10) -> dict[str, Any]:
    endpoint, request_url, pagination_enabled, page, page_size = _preview_request_details(source, entity)
    if not request_url:
        return {
            "available": False,
            "pagination_enabled": pagination_enabled,
            "page": page,
            "page_size": page_size,
            "received_count": 0,
            "mapped": [],
            "raw": [],
            "error": f"No hay endpoint configurado para {entity}.",
        }

    status_code, payload = await _request_json(request_url, _build_headers(source))
    rows = _extract_entity_rows(payload, endpoint, entity, status_code)
    mapping = _field_map(source)
    variants_count = sum(len(_as_list(item.get("variants"))) for item in rows)
    images_count = sum(len(_as_list(item.get("images"))) for item in rows)
    attributes_count = sum(
        len(_attribute_pairs(item.get("specs")))
        + len(_attribute_pairs(item.get("props")))
        + (1 if item.get("material") not in (None, "") else 0)
        for item in rows
    )
    return {
        "available": True,
        "request_url": _safe_preview_url(request_url),
        "status_code": status_code,
        "pagination_enabled": pagination_enabled,
        "page": page,
        "page_size": page_size,
        "received_count": len(rows),
        "mapped": [_preview_mapped_item(item, mapping, entity) for item in rows[:sample_limit]],
        "raw": rows[:sample_limit],
        "variants_count": variants_count,
        "images_count": images_count,
        "attributes_count": attributes_count,
    }


def _preview_error(source: IntegrationSource, entity: str, exc: Exception) -> dict[str, Any]:
    try:
        _, request_url, pagination_enabled, page, page_size = _preview_request_details(source, entity)
    except IntegrationRequestError:
        request_url, pagination_enabled, page, page_size = None, False, None, None
    return {
        "available": bool(request_url),
        "request_url": _safe_preview_url(request_url) if request_url else None,
        "status_code": getattr(exc, "status_code", None),
        "pagination_enabled": pagination_enabled,
        "page": page,
        "page_size": page_size,
        "received_count": 0,
        "mapped": [],
        "raw": [],
        "error": str(exc),
    }


async def preview_source(source: IntegrationSource) -> dict[str, Any]:
    validate_source(source)
    errors: list[str] = []
    try:
        products = await _preview_entity(source, "products")
    except (IntegrationRequestError, TypeError, ValueError) as exc:
        products = _preview_error(source, "products", exc)
    if products.get("error"):
        errors.append(f"Productos: {products['error']}")

    inventory = None
    if _endpoint_config(source, "inventory").get("path"):
        try:
            inventory = await _preview_entity(source, "inventory")
        except (IntegrationRequestError, TypeError, ValueError) as exc:
            inventory = _preview_error(source, "inventory", exc)
        if inventory.get("error"):
            errors.append(f"Inventario: {inventory['error']}")

    return {
        "success": not errors and bool(products.get("available")),
        "source_id": source.id,
        "message": "Vista previa generada. Solo se consultó la primera página y no se modificaron datos.",
        "products": products,
        "inventory": inventory,
        "errors": errors,
    }


async def _fetch_entity(source: IntegrationSource, entity: str) -> list[dict[str, Any]]:
    endpoint = _endpoint_config(source, entity)
    path = endpoint.get("path")
    if not path:
        return []
    url = _url_for(source, str(path))
    headers = _build_headers(source)
    pagination = _pagination_config(endpoint)
    if not pagination.get("enabled", False):
        status_code, payload = await _request_json(url, headers)
        return _extract_entity_rows(payload, endpoint, entity, status_code)

    if str(pagination.get("type", "page")).lower() != "page":
        raise IntegrationRequestError("La paginación configurada debe usar el tipo 'page'.")

    page_param = str(pagination.get("page_param") or "page")
    per_page_param = str(pagination.get("per_page_param") or "per_page")
    page = max(1, int(pagination.get("start_page") or 1))
    per_page = max(1, int(pagination.get("per_page") or 50))
    max_pages = max(1, int(pagination.get("max_pages") or 1000))
    all_items: list[dict[str, Any]] = []

    for _ in range(max_pages):
        page_url = _url_with_query(url, {page_param: page, per_page_param: per_page})
        status_code, payload = await _request_json(page_url, headers)
        page_items = _extract_entity_rows(payload, endpoint, entity, status_code)
        all_items.extend(page_items)

        if not page_items:
            break
        next_value = _value(payload, pagination.get("next_path")) if pagination.get("next_path") else None
        if pagination.get("next_path") and not next_value:
            break
        last_page = _as_float(_value(payload, pagination.get("last_page_path"))) if pagination.get("last_page_path") else None
        if last_page is not None and page >= last_page:
            break
        total = _as_float(_value(payload, pagination.get("total_path"))) if pagination.get("total_path") else None
        if total is not None and len(all_items) >= total:
            break
        if len(page_items) < per_page:
            break
        page += 1
    else:
        raise IntegrationRequestError(
            f"La sincronización de {entity} superó el máximo de {max_pages} páginas configurado."
        )

    return all_items


async def test_source(source: IntegrationSource) -> dict[str, Any]:
    validate_source(source)
    endpoint = _endpoint_config(source, "products")
    path = endpoint.get("path") or (source.configuration or {}).get("test_path") or "/"
    test_url = _url_for(source, str(path))
    pagination = _pagination_config(endpoint)
    if pagination.get("enabled", False):
        test_url = _url_with_query(
            test_url,
            {
                str(pagination.get("page_param") or "page"): max(1, int(pagination.get("start_page") or 1)),
                str(pagination.get("per_page_param") or "per_page"): max(1, int(pagination.get("per_page") or 50)),
            },
        )
    status_code, payload = await _request_json(test_url, _build_headers(source))
    sample_count = len(_extract_entity_rows(payload, endpoint, "products", status_code))
    return {
        "success": 200 <= status_code < 300,
        "status_code": status_code,
        "message": "Conexión exitosa con el origen de datos.",
        "sample_count": sample_count,
    }


async def _resolve_inventory_location(
    db: AsyncSession, source: IntegrationSource
) -> tuple[Branch | None, Warehouse | None]:
    configuration = source.configuration or {}
    branch_id = configuration.get("inventory_branch_id")
    warehouse_id = configuration.get("inventory_warehouse_id")

    branch_query = select(Branch).where(Branch.company_id == source.company_id, Branch.is_active.is_(True))
    if branch_id:
        branch_query = branch_query.where(Branch.id == branch_id)
    branch = (await db.execute(branch_query.order_by(Branch.created_at.asc()))).scalars().first()
    if not branch:
        return None, None

    warehouse_query = select(Warehouse).where(Warehouse.branch_id == branch.id, Warehouse.is_active.is_(True))
    if warehouse_id:
        warehouse_query = warehouse_query.where(Warehouse.id == warehouse_id)
    else:
        warehouse_query = warehouse_query.order_by(Warehouse.is_default.desc(), Warehouse.created_at.asc())
    warehouse = (await db.execute(warehouse_query)).scalars().first()
    return branch, warehouse


async def _find_link(
    db: AsyncSession, source_id: Any, entity_type: str, external_id: str
) -> IntegrationRecordLink | None:
    result = await db.execute(
        select(IntegrationRecordLink).where(
            IntegrationRecordLink.source_id == source_id,
            IntegrationRecordLink.entity_type == entity_type,
            IntegrationRecordLink.external_id == external_id,
        )
    )
    return result.scalars().first()


async def _find_link_by_sku(
    db: AsyncSession, source_id: Any, entity_type: str, external_sku: str
) -> IntegrationRecordLink | None:
    result = await db.execute(
        select(IntegrationRecordLink)
        .where(
            IntegrationRecordLink.source_id == source_id,
            IntegrationRecordLink.entity_type == entity_type,
            IntegrationRecordLink.external_sku == external_sku,
        )
        .order_by(IntegrationRecordLink.updated_at.desc())
        .limit(1)
    )
    return result.scalars().first()


async def _linked_product(
    db: AsyncSession,
    source: IntegrationSource,
    external_id: str | None,
    sku: str | None,
) -> Product | None:
    link = await _find_link(db, source.id, "product", external_id) if external_id else None
    if not link and sku:
        link = await _find_link_by_sku(db, source.id, "product", sku)
    product = await db.get(Product, link.local_product_id) if link and link.local_product_id else None
    if product and product.company_id == source.company_id:
        return product
    if sku:
        return (await db.execute(
            select(Product).where(Product.company_id == source.company_id, Product.sku == sku).limit(1)
        )).scalars().first()
    return None


async def _linked_variant(
    db: AsyncSession,
    source: IntegrationSource,
    external_id: str | None,
    sku: str | None,
) -> ProductVariant | None:
    link = await _find_link(db, source.id, "variant", external_id) if external_id else None
    if not link and sku:
        link = await _find_link_by_sku(db, source.id, "variant", sku)
    variant = await db.get(ProductVariant, link.local_variant_id) if link and link.local_variant_id else None
    if variant and variant.company_id == source.company_id:
        return variant
    if sku:
        return (await db.execute(
            select(ProductVariant).where(
                ProductVariant.company_id == source.company_id,
                ProductVariant.sku == sku,
            ).limit(1)
        )).scalars().first()
    return None


async def _load_embedded_inventory(
    db: AsyncSession,
    source: IntegrationSource,
    run: IntegrationSyncRun,
) -> list[dict[str, Any]]:
    """Read stock embedded in the catalog without modifying catalog records."""
    items = await _fetch_entity(source, "products")
    mapping = _field_map(source)
    collections = (source.configuration or {}).get("collections") or {}
    variants_path = collections.get("variants_path") or "variants[]"
    variants_prefix = str(variants_path)
    if not variants_prefix.endswith("[]"):
        variants_prefix = f"{variants_prefix}[]"
    embedded_inventory: list[dict[str, Any]] = []

    for item in items:
        external_id_value = _mapped(item, mapping, "product.external_id", "id", "external_id", "uuid")
        external_id = str(external_id_value).strip() if external_id_value not in (None, "") else None
        sku_value = _mapped(item, mapping, "product.sku", "sku", "code", "reference")
        sku = str(sku_value).strip() if sku_value not in (None, "") else None
        product = await _linked_product(db, source, external_id, sku)
        variant_items = _as_list(_value(item, variants_path))

        if variant_items:
            for variant_item in variant_items:
                if not isinstance(variant_item, dict):
                    continue
                quantity = _as_float(_mapped_context(
                    variant_item,
                    mapping,
                    "variant.stock",
                    variants_prefix,
                    "stock",
                    "quantity",
                    "available",
                    "inventory",
                ))
                if quantity is None:
                    continue
                variant_external_value = _mapped_context(
                    variant_item,
                    mapping,
                    "variant.external_id",
                    variants_prefix,
                    "variant_id",
                    "external_id",
                    "id",
                    "uuid",
                )
                variant_external_id = (
                    str(variant_external_value).strip() if variant_external_value not in (None, "") else None
                )
                variant_sku_value = _mapped_context(
                    variant_item,
                    mapping,
                    "variant.sku",
                    variants_prefix,
                    "sku",
                    "code",
                    "reference",
                )
                variant_sku = str(variant_sku_value).strip() if variant_sku_value not in (None, "") else None
                variant = await _linked_variant(db, source, variant_external_id, variant_sku)
                if not variant:
                    run.items_failed += 1
                    continue
                variant_product = await db.get(Product, variant.product_id)
                if not variant_product or variant_product.company_id != source.company_id:
                    run.items_failed += 1
                    continue
                embedded_inventory.append(
                    {
                        "product": variant_product,
                        "variant": variant,
                        "quantity": quantity,
                    }
                )
            continue

        quantity = _as_float(_mapped(item, mapping, "product.stock", "stock", "quantity", "available"))
        if quantity is None:
            continue
        if not product:
            run.items_failed += 1
            continue
        embedded_inventory.append({"product": product, "variant": None, "quantity": quantity})

    return embedded_inventory


async def _sync_products(
    db: AsyncSession, source: IntegrationSource, run: IntegrationSyncRun
) -> tuple[dict[str, Product], dict[str, ProductVariant], list[dict[str, Any]]]:
    items = await _fetch_entity(source, "products")
    mapping = _field_map(source)
    configuration = source.configuration or {}
    collections = configuration.get("collections") or {}
    variants_path = collections.get("variants_path") or "variants[]"
    variants_prefix = str(variants_path)
    if not variants_prefix.endswith("[]"):
        variants_prefix = f"{variants_prefix}[]"
    external_products: dict[str, Product] = {}
    external_variants: dict[str, ProductVariant] = {}
    embedded_inventory: list[dict[str, Any]] = []
    run.products_processed = len(items)

    for item in items:
        external_id = str(_mapped(item, mapping, "product.external_id", "id", "external_id", "uuid") or "").strip()
        name = str(_mapped(item, mapping, "product.name", "name", "title") or "").strip()
        if not external_id or not name:
            run.items_failed += 1
            continue

        sku_value = _mapped(item, mapping, "product.sku", "sku", "code", "reference")
        sku = str(sku_value).strip() if sku_value not in (None, "") else None
        link = await _find_link(db, source.id, "product", external_id)
        product = await db.get(Product, link.local_product_id) if link and link.local_product_id else None
        if product and product.company_id != source.company_id:
            product = None

        if not product and sku:
            product_result = await db.execute(
                select(Product).where(Product.company_id == source.company_id, Product.sku == sku).limit(1)
            )
            product = product_result.scalars().first()

        if product is None:
            product = Product(id=uuid.uuid4(), company_id=source.company_id, name=name, sku=sku)
            db.add(product)
            run.products_created += 1
        else:
            run.products_updated += 1

        product.name = name
        if sku is not None:
            product.sku = sku
        for field, key, *fallbacks in [
            ("description", "product.description", "description", "body_html"),
            ("image_url", "product.image_url", "image_url", "image"),
            ("barcode", "product.barcode", "barcode", "ean"),
        ]:
            value = _mapped(item, mapping, key, *fallbacks)
            if value not in (None, ""):
                setattr(product, field, str(value))
        for field, key, *fallbacks in [
            ("price", "product.price", "price", "sale_price"),
            ("cost", "product.cost", "cost", "purchase_price"),
        ]:
            value = _as_float(_mapped(item, mapping, key, *fallbacks))
            if value is not None:
                setattr(product, field, value)

        product_attributes = _collect_product_attributes(item, mapping)
        category_external_id = _mapped(item, mapping, "product.category.external_id", "category_id")
        category_name = _mapped(item, mapping, "product.category.name", "category_name")
        supplier_external_id = _mapped(item, mapping, "product.supplier.external_id", "provider_id", "supplier_id")
        supplier_name = _mapped(item, mapping, "product.supplier.name", "provider_name", "supplier_name")
        if category_external_id not in (None, ""):
            product_attributes["external_category_id"] = str(category_external_id)
        if category_name not in (None, ""):
            product.category_id = await _sync_category(db, source, str(category_name))
            product_attributes["category_name"] = str(category_name)
        if supplier_external_id not in (None, ""):
            product_attributes["external_supplier_id"] = str(supplier_external_id)
        if supplier_name not in (None, ""):
            product_attributes["supplier_name"] = str(supplier_name)
        for field, fallback in [("linea_id", "line_id"), ("linea_name", "line_name")]:
            value = _mapped(item, mapping, f"product.attributes.{field}", field, fallback)
            if value not in (None, ""):
                product_attributes[field] = value
        if product_attributes:
            product.attributes = {**(product.attributes or {}), **product_attributes}

        await _sync_product_images(db, source, product, item, mapping)

        # The integration link has a foreign key to the product, but no ORM
        # relationship tells SQLAlchemy about this dependency. Flush the
        # product explicitly before inserting or updating its external link.
        await db.flush()

        if not link:
            link = IntegrationRecordLink(
                id=uuid.uuid4(),
                company_id=source.company_id,
                source_id=source.id,
                entity_type="product",
                external_id=external_id,
            )
            db.add(link)
        link.local_product_id = product.id
        link.external_sku = sku
        link.last_synced_at = datetime.utcnow()
        link.raw_payload = item
        external_products[external_id] = product
        if sku:
            external_products[f"sku:{sku}"] = product

        variant_items = _as_list(_value(item, variants_path))
        for variant_item in variant_items:
            if not isinstance(variant_item, dict):
                continue
            variant_external_id = str(_mapped_context(
                variant_item,
                mapping,
                "variant.external_id",
                variants_prefix,
                "variant_id",
                "external_id",
                "id",
                "uuid",
            ) or "").strip()
            if not variant_external_id:
                run.items_failed += 1
                continue
            variant_sku_value = _mapped_context(
                variant_item, mapping, "variant.sku", variants_prefix, "sku", "code", "reference"
            )
            variant_sku = str(variant_sku_value).strip() if variant_sku_value not in (None, "") else None
            variant_name = str(_mapped_context(
                variant_item,
                mapping,
                "variant.name",
                variants_prefix,
                "name",
                "title",
                "medida",
                "size",
                "color",
            ) or f"Variante {variant_external_id}").strip()
            variant_link = await _find_link(db, source.id, "variant", variant_external_id)
            variant = await db.get(ProductVariant, variant_link.local_variant_id) if variant_link and variant_link.local_variant_id else None
            if variant and variant.product_id != product.id:
                variant = None
            if not variant and variant_sku:
                variant_result = await db.execute(
                    select(ProductVariant).where(
                        ProductVariant.product_id == product.id,
                        ProductVariant.sku == variant_sku,
                    ).limit(1)
                )
                variant = variant_result.scalars().first()
            if not variant:
                variant = ProductVariant(
                    id=uuid.uuid4(),
                    company_id=source.company_id,
                    product_id=product.id,
                    name=variant_name,
                    sku=variant_sku,
                )
                db.add(variant)
            else:
                variant.name = variant_name
                if variant_sku is not None:
                    variant.sku = variant_sku

            variant_price = _as_float(_mapped_context(
                variant_item, mapping, "variant.price", variants_prefix, "price", "sale_price", "selling_price"
            ))
            variant_cost = _as_float(_mapped_context(
                variant_item, mapping, "variant.cost", variants_prefix, "cost", "purchase_price"
            ))
            if variant_price is not None:
                variant.price = variant_price
                if _mapped(item, mapping, "product.price", "price", "sale_price") in (None, "") and product.price in (None, 0):
                    product.price = variant_price
                variant.price_extra = variant_price - float(product.price or 0)
            if variant_cost is not None:
                variant.cost = variant_cost
                if _mapped(item, mapping, "product.cost", "cost", "purchase_price") in (None, "") and product.cost in (None, 0):
                    product.cost = variant_cost
                variant.cost_extra = variant_cost - float(product.cost or 0)
            variant_barcode = _mapped_context(variant_item, mapping, "variant.barcode", variants_prefix, "barcode", "ean", "upc", "gtin", "item_code")
            if variant_barcode not in (None, ""):
                variant.barcode = str(variant_barcode)
            variant_attributes = _collect_variant_attributes(variant_item, mapping, variants_prefix)
            variant_stock_temp = _mapped_context(
                variant_item, mapping, "variant.stock_temp", variants_prefix, "stock_temp", "temporary_stock", "reserved"
            )
            if variant_stock_temp not in (None, ""):
                variant_attributes["stock_temp"] = variant_stock_temp
            if variant_attributes:
                variant.attributes = {**(variant.attributes or {}), **variant_attributes}

            # The integration link has a foreign key to the variant, but no ORM
            # relationship tells SQLAlchemy about this dependency. Flush the
            # variant explicitly before inserting its external link.
            await db.flush()

            if not variant_link:
                variant_link = IntegrationRecordLink(
                    id=uuid.uuid4(),
                    company_id=source.company_id,
                    source_id=source.id,
                    entity_type="variant",
                    external_id=variant_external_id,
                )
                db.add(variant_link)
            variant_link.local_product_id = product.id
            variant_link.local_variant_id = variant.id
            variant_link.external_sku = variant_sku
            variant_link.last_synced_at = datetime.utcnow()
            variant_link.raw_payload = variant_item
            external_variants[variant_external_id] = variant
            if variant_sku:
                external_variants[f"sku:{variant_sku}"] = variant

            variant_quantity = _as_float(_mapped_context(
                variant_item, mapping, "variant.stock", variants_prefix, "stock", "quantity", "available", "inventory"
            ))
            if variant_quantity is not None:
                embedded_inventory.append({
                    "product": product,
                    "variant": variant,
                    "external_id": variant_external_id,
                    "sku": variant_sku,
                    "quantity": variant_quantity,
                    "raw": variant_item,
                })

        if not variant_items:
            product_quantity = _as_float(_mapped(item, mapping, "product.stock", "stock", "quantity", "available"))
            if product_quantity is not None:
                embedded_inventory.append({
                    "product": product,
                    "variant": None,
                    "external_id": external_id,
                    "sku": sku,
                    "quantity": product_quantity,
                    "raw": item,
                })

    return external_products, external_variants, embedded_inventory


async def _sync_inventory(
    db: AsyncSession,
    source: IntegrationSource,
    run: IntegrationSyncRun,
    external_products: dict[str, Product] | None = None,
    external_variants: dict[str, ProductVariant] | None = None,
    embedded_inventory: list[dict[str, Any]] | None = None,
) -> None:
    external_products = external_products or {}
    external_variants = external_variants or {}
    items = await _fetch_entity(source, "inventory")
    if embedded_inventory is None:
        embedded_inventory = []
        if not _endpoint_config(source, "inventory").get("path"):
            embedded_inventory = await _load_embedded_inventory(db, source, run)
    if not items and not embedded_inventory:
        run.details = {**(run.details or {}), "inventory_message": "El origen no devolvió existencias."}
        return
    branch, warehouse = await _resolve_inventory_location(db, source)
    if not branch:
        run.items_failed += len(items) + len(embedded_inventory)
        run.details = {**(run.details or {}), "inventory_error": "La empresa no tiene una sucursal activa."}
        return

    mapping = _field_map(source)
    run.inventory_processed = len(items) + len(embedded_inventory)
    inventory_cache: dict[tuple[Any, Any, Any, Any, Any], Inventory] = {}
    warehouse_id = warehouse.id if warehouse else None

    async def upsert_inventory(
        product: Product, variant: ProductVariant | None, quantity: float
    ) -> None:
        cache_key = (source.company_id, product.id, branch.id, warehouse_id, variant.id if variant else None)
        cached_inventory = inventory_cache.get(cache_key)
        if cached_inventory:
            cached_inventory.quantity = quantity
            run.inventory_updated += 1
            return
        variant_filter = Inventory.variant_id == variant.id if variant else Inventory.variant_id.is_(None)
        inventory = (await db.execute(
            select(Inventory).where(
                Inventory.company_id == source.company_id,
                Inventory.product_id == product.id,
                variant_filter,
                Inventory.branch_id == branch.id,
                Inventory.warehouse_id == warehouse_id,
            ).limit(1)
        )).scalars().first()
        if not inventory:
            inventory = Inventory(
                id=uuid.uuid4(),
                company_id=source.company_id,
                product_id=product.id,
                variant_id=variant.id if variant else None,
                branch_id=branch.id,
                warehouse_id=warehouse_id,
            )
            db.add(inventory)
            # SessionLocal disables autoflush. Persist the new identity before
            # another payload record can look it up and create a duplicate.
            await db.flush()
        inventory_cache[cache_key] = inventory
        inventory.quantity = quantity
        run.inventory_updated += 1

    for embedded in embedded_inventory:
        await upsert_inventory(embedded["product"], embedded.get("variant"), embedded["quantity"])

    for item in items:
        variant_external_value = _mapped(
            item, mapping, "inventory.variant_external_id", "variant_id", "product_variant_id"
        )
        variant_external_id = (
            str(variant_external_value).strip() if variant_external_value not in (None, "") else None
        )
        variant_sku_value = _mapped(item, mapping, "inventory.variant_sku", "variant_sku", "sku")
        variant_sku = str(variant_sku_value).strip() if variant_sku_value not in (None, "") else None
        variant = (
            external_variants.get(variant_external_id or "")
            or (external_variants.get(f"sku:{variant_sku}") if variant_sku else None)
        )
        if not variant and (variant_external_id or variant_sku):
            variant = await _linked_variant(db, source, variant_external_id, variant_sku)
        external_id_value = _mapped(item, mapping, "inventory.external_id", "product_id", "id", "sku")
        external_id = str(external_id_value).strip() if external_id_value not in (None, "") else None
        sku_value = _mapped(item, mapping, "inventory.sku", "sku", "product_sku")
        sku = str(sku_value).strip() if sku_value not in (None, "") else None
        product = external_products.get(external_id or "") or (external_products.get(f"sku:{sku}") if sku else None)
        if variant:
            product = await db.get(Product, variant.product_id)
        if not product:
            product = await _linked_product(db, source, external_id, sku)
        quantity = _as_float(_mapped(item, mapping, "inventory.quantity", "quantity", "stock", "available"))
        if not product or product.company_id != source.company_id or quantity is None:
            run.items_failed += 1
            continue
        await upsert_inventory(product, variant, quantity)


async def enqueue_sync(
    db: AsyncSession,
    source: IntegrationSource,
    triggered_by_user_id: Any,
    *,
    sync_type: str,
    trigger_type: str = "MANUAL",
) -> IntegrationSyncRun:
    normalized_sync_type = sync_type.upper()
    normalized_trigger_type = trigger_type.upper()
    if normalized_sync_type not in {"CATALOG", "INVENTORY", "FULL"}:
        raise ValueError("Tipo de sincronización no soportado")
    if normalized_trigger_type not in {"MANUAL", "SCHEDULED"}:
        raise ValueError("Tipo de ejecución no soportado")
    active_run = (await db.execute(
        select(IntegrationSyncRun).where(
            IntegrationSyncRun.source_id == source.id,
            IntegrationSyncRun.sync_type == normalized_sync_type,
            IntegrationSyncRun.status.in_(["QUEUED", "RUNNING"]),
        ).limit(1)
    )).scalars().first()
    if active_run:
        raise IntegrationSyncConflict("Ya existe una sincronización de este tipo en cola o en ejecución.")

    now = datetime.utcnow()
    run = IntegrationSyncRun(
        id=uuid.uuid4(),
        company_id=source.company_id,
        source_id=source.id,
        triggered_by_user_id=triggered_by_user_id,
        created_by_id=triggered_by_user_id,
        sync_type=normalized_sync_type,
        trigger_type=normalized_trigger_type,
        status="QUEUED",
        queued_at=now,
        started_at=None,
        products_processed=0,
        products_created=0,
        products_updated=0,
        inventory_processed=0,
        inventory_updated=0,
        items_failed=0,
        details={},
    )
    db.add(run)
    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise IntegrationSyncConflict("Ya existe una sincronización de este tipo en cola o en ejecución.") from exc
    await db.refresh(run)
    return run


async def execute_sync_run(db: AsyncSession, run: IntegrationSyncRun) -> IntegrationSyncRun:
    run_id = run.id
    source_id = run.source_id
    source = await db.get(IntegrationSource, source_id)
    if not source:
        run.status = "FAILED"
        run.finished_at = datetime.utcnow()
        run.error_message = "El origen de datos ya no existe."
        await db.commit()
        return run

    try:
        validate_source(source)
        if run.sync_type in {"CATALOG", "FULL"}:
            products, variants, embedded_inventory = await _sync_products(db, source, run)
        else:
            products, variants, embedded_inventory = {}, {}, None
        if run.sync_type in {"INVENTORY", "FULL"}:
            await _sync_inventory(db, source, run, products, variants, embedded_inventory)
        run.status = "PARTIAL" if run.items_failed else "SUCCESS"
        run.finished_at = datetime.utcnow()
        source.status = "CONNECTED"
        source.last_synced_at = run.finished_at
        if run.sync_type in {"CATALOG", "FULL"}:
            source.last_catalog_synced_at = run.finished_at
        if run.sync_type in {"INVENTORY", "FULL"}:
            source.last_inventory_synced_at = run.finished_at
        source.last_sync_status = run.status
        source.last_error = None
        await db.commit()
    except Exception as exc:  # noqa: BLE001 - run status must be persisted for operator visibility
        await db.rollback()
        failed_run = await db.get(IntegrationSyncRun, run_id)
        failed_source = await db.get(IntegrationSource, source_id)
        if failed_run and failed_source:
            failed_run.status = "FAILED"
            failed_run.finished_at = datetime.utcnow()
            failed_run.error_message = str(exc)[:2000]
            failed_source.status = "ERROR"
            failed_source.last_sync_status = "FAILED"
            failed_source.last_error = str(exc)[:2000]
            await db.commit()
            return failed_run
    return run


async def sync_source(
    db: AsyncSession,
    source: IntegrationSource,
    triggered_by_user_id: Any,
    sync_type: str = "FULL",
) -> IntegrationSyncRun:
    """Backward-compatible synchronous entry point used by tests and internal callers."""
    run = await enqueue_sync(
        db,
        source,
        triggered_by_user_id,
        sync_type=sync_type,
        trigger_type="MANUAL",
    )
    run.status = "RUNNING"
    run.started_at = datetime.utcnow()
    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        queued_run = await db.get(IntegrationSyncRun, run.id)
        if queued_run and queued_run.status == "QUEUED":
            await db.delete(queued_run)
            await db.commit()
        raise IntegrationSyncConflict("Ya hay otra sincronización ejecutándose para este origen.") from exc
    return await execute_sync_run(db, run)
