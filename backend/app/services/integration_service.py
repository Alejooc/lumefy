from __future__ import annotations

import asyncio
import base64
from io import BytesIO
import ipaddress
import json
import logging
import os
from pathlib import Path
import re
import socket
import tempfile
import time
import uuid
from datetime import datetime
from typing import Any, Awaitable, Callable
from urllib import error as urlerror
from urllib import parse as urlparse
from urllib import request as urlrequest

from sqlalchemy import func, or_, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from PIL import Image, UnidentifiedImageError

from app.core.config import settings
from app.core.database import SessionLocal
from app.models.branch import Branch
from app.models.brand import Brand
from app.models.category import Category
from app.models.integration import IntegrationRecordLink, IntegrationSource, IntegrationSyncRun
from app.models.inventory import Inventory
from app.models.inventory_movement import InventoryMovement, MovementType
from app.models.product import Product
from app.models.product_image import ProductImage
from app.models.product_variant import ProductVariant
from app.models.warehouse import Warehouse
from app.models.supplier import Supplier
from app.models.unit_of_measure import UnitOfMeasure


class IntegrationRequestError(Exception):
    def __init__(self, message: str, status_code: int | None = None):
        super().__init__(message)
        self.status_code = status_code


class IntegrationSyncConflict(Exception):
    """Raised when an equivalent sync is already queued or running."""


LOGGER = logging.getLogger("lumefy.integration")
MAX_SYNC_ERROR_SAMPLES = 100


ProgressCallback = Callable[[dict[str, Any]], Awaitable[None]]


async def _report_progress(
    progress_callback: ProgressCallback | None,
    *,
    stage: str,
    message: str,
    percent: int,
    current: int = 0,
    total: int | None = None,
    entity: str | None = None,
    page: int | None = None,
    pages_total: int | None = None,
    items_received: int | None = None,
    items_total: int | None = None,
    items_failed: int | None = None,
    created: int | None = None,
    updated: int | None = None,
) -> None:
    if not progress_callback:
        return
    progress: dict[str, Any] = {
        "stage": stage,
        "message": message,
        "percent": max(0, min(100, int(percent))),
        "current": max(0, int(current)),
    }
    for key, value in {
        "total": total,
        "entity": entity,
        "page": page,
        "pages_total": pages_total,
        "items_received": items_received,
        "items_total": items_total,
        "items_failed": items_failed,
        "created": created,
        "updated": updated,
    }.items():
        if value is not None:
            progress[key] = value
    await progress_callback(progress)


def _record_sync_item_error(
    run: IntegrationSyncRun,
    reason: str,
    **context: Any,
) -> None:
    """Keep bounded, actionable diagnostics for records skipped by a sync.

    The provider payload is intentionally not stored here: it can be very
    large and may contain credentials or customer data. Only a small set of
    scalar identifiers is retained for the operator to locate the bad row.
    """
    details = dict(run.details or {})
    counts = dict(details.get("error_counts") or {})
    counts[reason] = int(counts.get(reason, 0)) + 1
    samples = list(details.get("error_samples") or [])
    if len(samples) < MAX_SYNC_ERROR_SAMPLES:
        sample: dict[str, str] = {"reason": reason}
        for key, value in context.items():
            if value in (None, "") or isinstance(value, (dict, list, tuple, set)):
                continue
            text = str(value).strip()
            if text:
                sample[str(key)] = text[:200]
        samples.append(sample)
    details["error_counts"] = counts
    details["error_samples"] = samples
    run.details = details


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


def _retry_delay(attempt: int, retry_after: Any = None) -> float:
    """Return a bounded delay for one transient provider failure."""
    try:
        requested = float(str(retry_after).strip()) if retry_after not in (None, "") else None
    except (TypeError, ValueError):
        requested = None
    if requested is None:
        requested = settings.INTEGRATION_RETRY_BASE_SECONDS * (2**attempt)
    return max(0.0, min(float(requested), settings.INTEGRATION_RETRY_MAX_SECONDS))


def _read_limited(response: Any, *, limit: int, too_large_message: str) -> bytes:
    content_length = response.headers.get("Content-Length") if getattr(response, "headers", None) else None
    try:
        if content_length and int(content_length) > limit:
            raise IntegrationRequestError(too_large_message, 413)
    except ValueError as exc:
        raise IntegrationRequestError("El proveedor devolvió un tamaño de respuesta inválido.") from exc
    body = response.read(limit + 1)
    if len(body) > limit:
        raise IntegrationRequestError(too_large_message, 413)
    return body


def _request_json_sync(url: str, headers: dict[str, str]) -> tuple[int, Any]:
    _validate_outbound_url(url)
    request = urlrequest.Request(url, headers=headers, method="GET")
    opener = urlrequest.build_opener(_SafeRedirectHandler(_origin(_validate_url_syntax(url))))
    last_error: IntegrationRequestError | None = None
    retry_attempts = settings.INTEGRATION_RETRY_ATTEMPTS
    for attempt in range(retry_attempts + 1):
        try:
            with opener.open(request, timeout=settings.INTEGRATION_REQUEST_TIMEOUT_SECONDS) as response:
                status_code = int(response.getcode())
                if status_code == 429 or 500 <= status_code <= 599:
                    try:
                        detail = _read_limited(
                            response,
                            limit=1024,
                            too_large_message="La respuesta de error del proveedor supera el tamaño permitido.",
                        ).decode("utf-8", errors="replace")[:500]
                    except IntegrationRequestError:
                        detail = ""
                    last_error = IntegrationRequestError(
                        f"La API respondió HTTP {status_code}. {detail}".strip(), status_code
                    )
                    if attempt < retry_attempts:
                        time.sleep(_retry_delay(attempt, response.headers.get("Retry-After")))
                        continue
                    raise last_error
                body = _read_limited(
                    response,
                    limit=settings.INTEGRATION_MAX_RESPONSE_BYTES,
                    too_large_message="La respuesta de la API supera el tamaño permitido.",
                ).decode("utf-8")
                try:
                    return status_code, json.loads(body) if body else {}
                except json.JSONDecodeError as exc:
                    raise IntegrationRequestError("La respuesta de la API no es JSON válido.", status_code) from exc
        except urlerror.HTTPError as exc:
            retryable = exc.code == 429 or 500 <= exc.code <= 599
            try:
                detail = exc.read(1024).decode("utf-8", errors="replace")[:500]
            except Exception:
                detail = ""
            last_error = IntegrationRequestError(
                f"La API respondió HTTP {exc.code}. {detail}".strip(), exc.code
            )
            if retryable and attempt < retry_attempts:
                time.sleep(_retry_delay(attempt, exc.headers.get("Retry-After")))
                continue
            raise last_error from exc
        except (urlerror.URLError, TimeoutError, OSError) as exc:
            last_error = IntegrationRequestError(f"No se pudo conectar con la API: {exc}")
            if attempt < retry_attempts:
                time.sleep(_retry_delay(attempt))
                continue
            raise last_error from exc
    raise last_error or IntegrationRequestError("No se pudo completar la petición al proveedor.")


async def _request_json(url: str, headers: dict[str, str]) -> tuple[int, Any]:
    return await asyncio.to_thread(_request_json_sync, url, headers)


MAX_PROXY_ASSET_BYTES = 10 * 1024 * 1024
LOCAL_INTEGRATION_ASSET_PREFIX = "/static/uploads/integrations"
LOCAL_IMAGE_EXTENSIONS = {
    "image/jpeg": ".jpg",
    "image/jpg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
    "image/gif": ".gif",
}


def _integration_asset_directory() -> Path:
    configured_directory = os.getenv("INTEGRATION_ASSET_DIR")
    if configured_directory:
        return Path(configured_directory)
    # This resolves to /app/static/uploads/integrations in the production
    # worker and backend containers, which share the backend_static volume.
    return Path(__file__).resolve().parents[2] / "static" / "uploads" / "integrations"


def _local_asset_key(source: IntegrationSource, provider_url: str) -> str:
    import hashlib

    return hashlib.sha256(f"{source.id}:{provider_url}".encode("utf-8")).hexdigest()


def _local_asset_url(source: IntegrationSource, provider_url: str, extension: str) -> str:
    return f"{LOCAL_INTEGRATION_ASSET_PREFIX}/{source.id}/{_local_asset_key(source, provider_url)}{extension}"


def _local_asset_file_candidates(source: IntegrationSource, provider_url: str) -> list[tuple[str, Path]]:
    directory = _integration_asset_directory() / str(source.id)
    key = _local_asset_key(source, provider_url)
    return [
        (
            _local_asset_url(source, provider_url, extension),
            directory / f"{key}{extension}",
        )
        for extension in LOCAL_IMAGE_EXTENSIONS.values()
    ]


async def _cache_provider_asset(source: IntegrationSource, provider_url: str) -> str | None:
    """Download one provider image to the shared VPS volume.

    The URL hash makes downloads idempotent. Existing local files are served
    without contacting the provider again. A failed refresh returns ``None``
    so the caller can retain the previous local image instead of replacing it
    with a broken URL.
    """

    normalized_url = (provider_url or "").strip()
    if not normalized_url:
        return None

    for local_url, target_path in _local_asset_file_candidates(source, normalized_url):
        if target_path.is_file() and target_path.stat().st_size > 0:
            return local_url

    try:
        content_type, body = await request_asset(source, normalized_url)
        extension = LOCAL_IMAGE_EXTENSIONS.get(content_type.lower())
        if not extension:
            raise IntegrationRequestError("Formato de imagen no permitido para almacenamiento local.", 415)
        try:
            with Image.open(BytesIO(body)) as image:
                image.verify()
        except (Image.DecompressionBombError, UnidentifiedImageError, OSError, SyntaxError, ValueError) as exc:
            raise IntegrationRequestError("El proveedor devolvió una imagen corrupta.", 422) from exc

        directory = _integration_asset_directory() / str(source.id)
        directory.mkdir(parents=True, exist_ok=True)
        target_path = directory / f"{_local_asset_key(source, normalized_url)}{extension}"
        if not target_path.is_file() or target_path.stat().st_size == 0:
            descriptor, temporary_path = tempfile.mkstemp(prefix=".asset-", dir=directory)
            try:
                with os.fdopen(descriptor, "wb") as output:
                    output.write(body)
                    output.flush()
                    os.fsync(output.fileno())
                os.replace(temporary_path, target_path)
            except Exception:
                if os.path.exists(temporary_path):
                    os.unlink(temporary_path)
                raise
        return _local_asset_url(source, normalized_url, extension)
    except (IntegrationRequestError, OSError) as exc:
        LOGGER.warning("No se pudo guardar la imagen externa %s: %s", normalized_url, exc)
        return None


def _is_local_integration_asset(value: str | None) -> bool:
    return bool(value and value.startswith(f"{LOCAL_INTEGRATION_ASSET_PREFIX}/"))


_LOCAL_ASSET_FILENAME = re.compile(r"^[0-9a-f]{64}\.(?:jpg|png|webp|gif)$")


def _local_integration_asset_path(value: str | None) -> Path | None:
    """Resolve one generated local asset URL without allowing path traversal."""
    if not _is_local_integration_asset(value):
        return None

    relative = value[len(f"{LOCAL_INTEGRATION_ASSET_PREFIX}/") :]
    parts = relative.split("/")
    if len(parts) != 2 or not parts[0] or not _LOCAL_ASSET_FILENAME.fullmatch(parts[1]):
        return None
    try:
        uuid.UUID(parts[0])
    except ValueError:
        return None

    root = _integration_asset_directory().resolve()
    candidate = (root / parts[0] / parts[1]).resolve()
    if root not in candidate.parents:
        return None
    return candidate


async def remove_unreferenced_local_assets(
    db: AsyncSession,
    asset_urls: set[str],
) -> int:
    """Remove cached provider files no longer referenced by any product."""
    normalized_urls = {
        str(value).strip()
        for value in asset_urls
        if _local_integration_asset_path(value) is not None
    }
    if not normalized_urls:
        return 0

    product_refs = await db.execute(
        select(Product.image_url).where(Product.image_url.in_(normalized_urls))
    )
    image_refs = await db.execute(
        select(ProductImage.image_url).where(ProductImage.image_url.in_(normalized_urls))
    )
    referenced = {
        str(value).strip()
        for value in [*product_refs.scalars().all(), *image_refs.scalars().all()]
        if value
    }
    removable = normalized_urls - referenced
    if not removable:
        return 0

    def unlink_files() -> int:
        removed = 0
        for value in removable:
            path = _local_integration_asset_path(value)
            if path is None:
                continue
            try:
                path.unlink()
            except FileNotFoundError:
                continue
            except OSError:
                LOGGER.warning("No se pudo eliminar la imagen local %s", path)
                continue
            removed += 1
        return removed

    removed = await asyncio.to_thread(unlink_files)
    for value in removable:
        path = _local_integration_asset_path(value)
        if path is None:
            continue
        try:
            path.parent.rmdir()
        except OSError:
            pass
    return removed


async def prune_orphaned_local_assets(db: AsyncSession) -> int:
    """Remove old generated files that no longer have a database reference."""
    root = _integration_asset_directory()
    if not root.is_dir():
        return 0

    files = [path for path in root.glob("*/*") if path.is_file()]
    if not files:
        return 0

    product_refs = await db.execute(
        select(Product.image_url).where(Product.image_url.like(f"{LOCAL_INTEGRATION_ASSET_PREFIX}/%"))
    )
    image_refs = await db.execute(
        select(ProductImage.image_url).where(ProductImage.image_url.like(f"{LOCAL_INTEGRATION_ASSET_PREFIX}/%"))
    )
    referenced = {
        str(value).strip()
        for value in [*product_refs.scalars().all(), *image_refs.scalars().all()]
        if value
    }

    orphaned = []
    for path in files:
        try:
            relative = path.relative_to(root)
        except ValueError:
            continue
        if len(relative.parts) != 2:
            continue
        value = f"{LOCAL_INTEGRATION_ASSET_PREFIX}/{relative.parts[0]}/{relative.parts[1]}"
        if _local_integration_asset_path(value) is not None and value not in referenced:
            orphaned.append(path)

    def unlink_files() -> int:
        removed = 0
        for path in orphaned:
            try:
                path.unlink()
            except FileNotFoundError:
                continue
            except OSError:
                LOGGER.warning("No se pudo eliminar la imagen local huérfana %s", path)
                continue
            removed += 1
        return removed

    removed = await asyncio.to_thread(unlink_files)
    for path in {item.parent for item in orphaned}:
        try:
            path.rmdir()
        except OSError:
            pass
    return removed


def _asset_url_matches_source(source: IntegrationSource, url: str) -> bool:
    """Check that an asset URL belongs to this source's configured path."""
    try:
        target = _validate_url_syntax(url)
        configuration = source.configuration or {}
        base_value = str(configuration.get("asset_base_url") or source.base_url or "").strip()
        base = _validate_url_syntax(base_value)
    except (IntegrationRequestError, TypeError, ValueError):
        return False

    if _origin(target) != _origin(base):
        return False
    base_path = base.path.rstrip("/")
    if not base_path or base_path == "/":
        return True
    target_path = target.path.rstrip("/") or "/"
    return target_path == base_path or target_path.startswith(f"{base_path}/")


def _request_asset_sync(url: str, headers: dict[str, str]) -> tuple[str, bytes]:
    """Fetch one provider image while retaining the integration auth headers."""
    _validate_outbound_url(url)
    request_headers = dict(headers)
    request_headers["Accept"] = "image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8"
    request = urlrequest.Request(url, headers=request_headers, method="GET")
    opener = urlrequest.build_opener(_SafeRedirectHandler(_origin(_validate_url_syntax(url))))
    retry_attempts = settings.INTEGRATION_RETRY_ATTEMPTS
    for attempt in range(retry_attempts + 1):
        try:
            with opener.open(request, timeout=settings.INTEGRATION_REQUEST_TIMEOUT_SECONDS) as response:
                content_type = (response.headers.get_content_type() or "").lower()
                status_code = int(response.getcode())
                if status_code == 429 or 500 <= status_code <= 599:
                    if attempt < retry_attempts:
                        time.sleep(_retry_delay(attempt, response.headers.get("Retry-After")))
                        continue
                    raise IntegrationRequestError("El proveedor no pudo entregar la imagen.", status_code)
                if not content_type.startswith("image/"):
                    raise IntegrationRequestError("El proveedor no devolvió una imagen válida.", status_code)
                body = _read_limited(
                    response,
                    limit=MAX_PROXY_ASSET_BYTES,
                    too_large_message="La imagen del proveedor supera el tamaño permitido.",
                )
                return content_type, body
        except urlerror.HTTPError as exc:
            retryable = exc.code == 429 or 500 <= exc.code <= 599
            if retryable and attempt < retry_attempts:
                time.sleep(_retry_delay(attempt, exc.headers.get("Retry-After")))
                continue
            raise IntegrationRequestError("El proveedor no pudo entregar la imagen.", exc.code) from exc
        except (urlerror.URLError, TimeoutError, OSError) as exc:
            if attempt < retry_attempts:
                time.sleep(_retry_delay(attempt))
                continue
            raise IntegrationRequestError(f"No se pudo conectar con el proveedor de imágenes: {exc}") from exc
        except ValueError as exc:
            raise IntegrationRequestError("El proveedor devolvió un tamaño de imagen inválido.") from exc
    raise IntegrationRequestError("No se pudo completar la descarga de la imagen.")


async def request_asset(source: IntegrationSource, url: str) -> tuple[str, bytes]:
    return await asyncio.to_thread(_request_asset_sync, url, _build_headers(source))


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


def _as_bool(value: Any, default: bool | None = None) -> bool | None:
    """Parse the common boolean representations returned by providers."""

    if value in (None, ""):
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    normalized = str(value).strip().casefold()
    if normalized in {"1", "true", "yes", "y", "si", "sí", "on", "active", "activo"}:
        return True
    if normalized in {"0", "false", "no", "n", "off", "inactive", "inactivo"}:
        return False
    return default


def _as_text(value: Any, *keys: str) -> str | None:
    """Extract a usable label from scalar or object-shaped provider values."""

    if value in (None, ""):
        return None
    if isinstance(value, dict):
        for key in keys or ("name", "title", "label", "value", "code", "id"):
            nested = value.get(key)
            if nested not in (None, "") and not isinstance(nested, (dict, list)):
                text = str(nested).strip()
                if text:
                    return text
        return None
    text = str(value).strip()
    return text or None


def _as_choice(value: Any, choices: set[str]) -> str | None:
    text = _as_text(value)
    if not text:
        return None
    normalized = text.upper()
    return normalized if normalized in choices else None


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
        if not data and entity in {"products", "inventory"} and any(
            key in payload
            for key in (
                "product_id",
                "product_name",
                "name",
                "title",
                "variants",
                "sku",
                "stock",
                "quantity",
                "available",
            )
        ):
            data = [payload]
    if not isinstance(data, list):
        raise IntegrationRequestError(f"El endpoint de {entity} no devolvió una lista de registros.", status_code)
    return [item for item in data if isinstance(item, dict)]


def _pagination_config(endpoint: dict[str, Any]) -> dict[str, Any]:
    pagination = endpoint.get("pagination") or {}
    return pagination if isinstance(pagination, dict) else {}


def _inventory_batch_config(endpoint: dict[str, Any]) -> dict[str, Any]:
    """Return a safe SKU-batch configuration for inventory endpoints.

    Providers commonly cap the bulk inventory endpoint at 100 SKU values. The
    cap is enforced here even if a source was configured manually with a larger
    value, so a bad configuration can never produce an oversized request.
    """

    batch = endpoint.get("batch") or endpoint.get("sku_batch") or {}
    if not isinstance(batch, dict) or batch.get("enabled") is not True:
        return {}
    query_param = str(batch.get("query_param") or batch.get("sku_query_param") or "skus").strip()
    if not query_param:
        raise IntegrationRequestError("El parámetro de lotes de inventario no puede estar vacío.")
    try:
        requested_size = int(batch.get("size") or batch.get("batch_size") or 100)
    except (TypeError, ValueError) as exc:
        raise IntegrationRequestError("El tamaño de lote de inventario debe ser un número entero.") from exc
    return {
        "enabled": True,
        "query_param": query_param,
        "size": min(100, max(1, requested_size)),
    }


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
    add("product.internal_reference", ("internal_reference", "internal_code", "codigo_interno"))
    add("product.barcode", ("barcode", "ean", "upc", "gtin"))
    add("product.price", ("sale_price", "selling_price", "price"))
    add("product.cost", ("purchase_price", "cost"))
    add("product.category.external_id", ("category_id",))
    add("product.category.name", ("category_name", "category", "categoria", "nombre_categoria"))
    add(
        "product.brand.external_id",
        ("brand_id", "brand_external_id", "brand_code", "brand_uuid", "manufacturer_id", "marca_id"),
    )
    add(
        "product.brand.name",
        ("brand_name", "brand", "brand_title", "manufacturer", "manufacturer_name", "marca", "nombre_marca"),
    )
    add("product.supplier.external_id", ("provider_id", "supplier_id", "vendor_id"))
    add("product.supplier.name", ("provider_name", "supplier_name", "vendor_name"))
    add("product.weight", ("weight", "weight_kg", "product_weight", "peso", "peso_kg"))
    add("product.volume", ("volume", "volume_l", "product_volume", "volumen", "volumen_l"))
    add("product.tax_rate", ("tax_rate", "tax", "vat", "iva", "impuesto"))
    add("product.min_stock", ("min_stock", "minimum_stock", "reorder_point", "stock_minimo"))
    add("product.product_type", ("product_type", "product_kind", "kind", "tipo_producto"))
    add("product.track_inventory", ("track_inventory", "manage_stock", "inventory_tracked", "control_inventario"))
    add("product.tracking_type", ("tracking_type", "tracking", "tipo_seguimiento"))
    add("product.sale_ok", ("sale_ok", "sellable", "can_sell", "allow_sale"))
    add("product.purchase_ok", ("purchase_ok", "purchasable", "can_purchase", "allow_purchase"))
    add(
        "product.unit.name",
        ("unit_name", "unit_of_measure", "uom", "unidad", "unidad_medida", "unit"),
    )
    add(
        "product.purchase_unit.name",
        ("purchase_unit_name", "purchase_uom", "unidad_compra", "unidad_compra_nombre"),
    )
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
        warnings.append("El proveedor se homologará automáticamente: se reutiliza si existe y se crea si no existe.")
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
    parsed_url = urlparse.urlsplit(url)
    if parsed_url.scheme in {"http", "https"} and parsed_url.netloc:
        return url
    configuration = source.configuration or {}
    base_url = str(configuration.get("asset_base_url") or source.base_url or "").strip()
    parsed_base = urlparse.urlsplit(base_url)
    if parsed_base.scheme in {"http", "https"} and parsed_base.netloc:
        # Join URL paths explicitly. ``products/12529/9_b4.jpg`` must remain
        # intact; only the configured host/base path is prepended.
        base_path = parsed_base.path.rstrip("/")
        relative_path = parsed_url.path.lstrip("/")
        joined_path = f"{base_path}/{relative_path}" if base_path else f"/{relative_path}"
        return urlparse.urlunsplit(
            (parsed_base.scheme, parsed_base.netloc, joined_path, parsed_url.query, parsed_url.fragment)
        )
    return urlparse.urljoin(base_url.rstrip("/") + "/", url.lstrip("/"))


async def _sync_category(
    db: AsyncSession, source: IntegrationSource, name: str | None
) -> uuid.UUID | None:
    normalized = _as_text(name, "name", "title", "label") or ""
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


async def _sync_brand(
    db: AsyncSession,
    source: IntegrationSource,
    external_id: Any = None,
    name: Any = None,
) -> Brand | None:
    """Resolve a provider brand by tenant-scoped name and create it if absent.

    Brands currently do not have a dedicated external-id column.  We still
    retain the provider id in the product attributes, while the normalized
    brand name is the stable local homologation key.  This also handles
    providers that only return ``brand``/``marca`` as a scalar or nested
    object.
    """

    normalized_external_id = _as_text(external_id, "id", "code", "value")
    normalized_name = _as_text(name, "name", "title", "label", "value")
    if not normalized_name and normalized_external_id:
        normalized_name = f"Marca {normalized_external_id}"
    if not normalized_name:
        return None

    result = await db.execute(
        select(Brand).where(
            Brand.company_id == source.company_id,
            func.lower(func.trim(Brand.name)) == normalized_name.casefold(),
        ).limit(1)
    )
    brand = result.scalars().first()
    if brand:
        # A previously archived brand should become usable again when the
        # provider sends it in an authoritative catalog sync.
        if not brand.is_active:
            brand.is_active = True
        return brand

    brand = Brand(
        id=uuid.uuid4(),
        company_id=source.company_id,
        name=normalized_name,
    )
    db.add(brand)
    await db.flush()
    return brand


async def _sync_unit_of_measure(
    db: AsyncSession,
    source: IntegrationSource,
    name: Any = None,
) -> UnitOfMeasure | None:
    """Resolve or create a tenant-scoped unit of measure by name/abbreviation."""

    normalized = _as_text(name, "name", "title", "label", "value", "code")
    if not normalized or normalized.isdigit():
        return None
    result = await db.execute(
        select(UnitOfMeasure).where(
            UnitOfMeasure.company_id == source.company_id,
            UnitOfMeasure.is_active.is_(True),
            or_(
                func.lower(func.trim(UnitOfMeasure.name)) == normalized.casefold(),
                func.lower(func.trim(UnitOfMeasure.abbreviation)) == normalized.casefold(),
            ),
        ).limit(1)
    )
    unit = result.scalars().first()
    if unit:
        return unit

    unit = UnitOfMeasure(
        id=uuid.uuid4(),
        company_id=source.company_id,
        name=normalized,
        abbreviation=normalized[:10],
    )
    db.add(unit)
    await db.flush()
    return unit


async def _sync_supplier(
    db: AsyncSession,
    source: IntegrationSource,
    external_id: Any = None,
    name: Any = None,
) -> Supplier | None:
    """Resolve an external supplier and create it when the catalog introduces it.

    External IDs are the primary key for homologation. A normalized name is a
    fallback for older sources that do not provide an ID. The lookup is scoped
    to the tenant so suppliers are never shared between companies.
    """
    normalized_external_id = _as_text(external_id, "id", "code", "value")
    normalized_name = _as_text(name, "name", "title", "label", "value")
    if not normalized_external_id and not normalized_name:
        return None

    supplier: Supplier | None = None
    if normalized_external_id:
        result = await db.execute(
            select(Supplier).where(
                Supplier.company_id == source.company_id,
                Supplier.external_id == normalized_external_id,
            ).limit(1)
        )
        supplier = result.scalars().first()

    if not supplier and normalized_name:
        result = await db.execute(
            select(Supplier).where(
                Supplier.company_id == source.company_id,
                func.lower(func.trim(Supplier.name)) == normalized_name.casefold(),
            ).limit(1)
        )
        supplier = result.scalars().first()

    if supplier:
        if normalized_external_id and not supplier.external_id:
            supplier.external_id = normalized_external_id
        if normalized_name and not supplier.name:
            supplier.name = normalized_name
        return supplier

    supplier = Supplier(
        id=uuid.uuid4(),
        company_id=source.company_id,
        external_id=normalized_external_id,
        name=normalized_name or f"Proveedor {normalized_external_id}",
    )
    db.add(supplier)
    await db.flush()
    return supplier


async def _sync_product_images(
    db: AsyncSession, source: IntegrationSource, product: Product, item: dict[str, Any], mapping: dict[str, Any]
) -> None:
    path = _mapping_path(mapping, "product.images")
    if not path:
        path = (source.configuration or {}).get("collections", {}).get("images_path")
    image_items = _as_list(_value(item, path)) if path else []
    if not image_items:
        return

    # The provider response is authoritative when it contains an image list.
    # Older versions only appended missing rows, so a URL-base correction or a
    # changed provider payload left stale/broken images attached forever. Build
    # the provider snapshot first, then replace each URL with its local VPS
    # copy before reconciling rows below.
    provider_incoming: list[tuple[int, int, str]] = []
    seen_urls: set[str] = set()
    for index, image in enumerate(image_items):
        if isinstance(image, str):
            image_url = _asset_url(source, image)
            order = index
        elif isinstance(image, dict):
            image_url = _asset_url(
                source,
                image.get("url")
                or image.get("image_url")
                or image.get("src")
                or image.get("image")
                or image.get("path"),
            )
            try:
                raw_order = image.get("order")
                if raw_order in (None, ""):
                    raw_order = image.get("position")
                order = int(raw_order) if raw_order not in (None, "") else index
            except (TypeError, ValueError):
                order = index
        else:
            continue
        if not image_url:
            continue
        normalized_url = image_url.strip()
        url_key = normalized_url.casefold()
        if not normalized_url or url_key in seen_urls:
            continue
        seen_urls.add(url_key)
        provider_incoming.append((order, index, normalized_url))

    if not provider_incoming:
        return

    provider_incoming.sort(key=lambda value: (value[0], value[1]))
    existing_rows = (
        await db.execute(
            select(ProductImage)
            .where(ProductImage.product_id == product.id)
            .order_by(ProductImage.order, ProductImage.id)
        )
    ).scalars().all()
    incoming: list[tuple[int, int, str]] = []
    for order, index, provider_url in provider_incoming:
        local_url = await _cache_provider_asset(source, provider_url)
        if not local_url:
            # Never replace a previously good local copy with a broken
            # provider URL. A later catalog run can retry the failed download.
            fallback = next(
                (
                    row
                    for row in existing_rows
                    if (row.order or 0) == order and _is_local_integration_asset(row.image_url)
                ),
                None,
            )
            local_url = fallback.image_url if fallback else None
        if local_url:
            incoming.append((order, index, local_url))

    # Keep the provider references for traceability and for future refreshes,
    # while product.image_url and ProductImage.image_url point to local files.
    product.attributes = {
        **(getattr(product, "attributes", None) or {}),
        "external_image_urls": [provider_url for _order, _index, provider_url in provider_incoming],
    }
    if not incoming:
        return

    existing_by_url = {
        str(row.image_url).strip().casefold(): row
        for row in existing_rows
        if row.image_url and str(row.image_url).strip()
    }
    used_ids: set[Any] = set()

    for order, _index, image_url in incoming:
        url_key = image_url.casefold()
        existing = existing_by_url.get(url_key)
        if existing is not None and existing.id in used_ids:
            existing = None

        # Reuse a row at the same position when the provider changed the URL.
        # This keeps the table small and fixes stale URLs without recreating
        # every row on every catalog run.
        if existing is None:
            existing = next(
                (
                    row
                    for row in existing_rows
                    if row.id not in used_ids and (row.order or 0) == order
                ),
                None,
            )

        if existing is None:
            existing = ProductImage(
                id=uuid.uuid4(),
                product_id=product.id,
                image_url=image_url,
                order=order,
            )
            db.add(existing)
        else:
            existing.image_url = image_url
            existing.order = order
        used_ids.add(existing.id)

    # Remove rows that no longer exist in the provider response.  This is what
    # clears old malformed bases and duplicate entries after the next sync.
    for row in existing_rows:
        if row.id not in used_ids:
            await db.delete(row)

    product.image_url = incoming[0][2]


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
            "brand": _as_text(
                _mapped(
                    item,
                    mapping,
                    "product.brand.name",
                    "brand_name",
                    "brand",
                    "manufacturer",
                    "manufacturer_name",
                    "marca",
                ),
                "name",
                "title",
                "label",
            ),
            "weight": _as_float(_mapped(item, mapping, "product.weight", "weight", "weight_kg", "peso", "peso_kg")),
            "volume": _as_float(_mapped(item, mapping, "product.volume", "volume", "volume_l", "volumen", "volumen_l")),
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


def _preflight_auth(source: IntegrationSource) -> tuple[bool, str]:
    """Validate only the local credential shape; no secret is returned."""
    auth_type = (source.auth_type or "none").strip().lower()
    credentials = source.credentials or {}
    if auth_type in {"none", ""}:
        return True, "Sin autenticación configurada."
    if auth_type == "bearer":
        return (
            bool(credentials.get("token") or credentials.get("access_token")),
            "Token Bearer configurado." if credentials.get("token") or credentials.get("access_token") else "Falta el token Bearer.",
        )
    if auth_type in {"api_key", "apikey"}:
        configured = bool(credentials.get("api_key") or credentials.get("token"))
        return configured, "API key configurada." if configured else "Falta la API key."
    if auth_type == "basic":
        configured = bool(credentials.get("username") and credentials.get("password"))
        return configured, "Credenciales Basic configuradas." if configured else "Faltan usuario o contraseña Basic."
    if auth_type == "custom_headers":
        headers = credentials.get("headers")
        configured = bool(isinstance(headers, dict) and headers)
        return configured, "Encabezados personalizados configurados." if configured else "Faltan los encabezados personalizados."
    return False, f"Tipo de autenticación no soportado: {auth_type}."


async def preflight_source(db: AsyncSession, source: IntegrationSource) -> dict[str, Any]:
    """Run a bounded, read-only compatibility check before queuing a sync."""
    checks: list[dict[str, Any]] = []
    warnings: list[str] = []
    errors: list[str] = []

    def add_check(code: str, ok: bool, message: str, *, severity: str = "error", **details: Any) -> None:
        checks.append({"code": code, "ok": ok, "severity": severity, "message": message, **details})
        if ok:
            return
        if severity == "warning":
            warnings.append(message)
        else:
            errors.append(message)

    try:
        validate_source(source)
        add_check("base_url", True, "La URL base es válida y apunta a un origen permitido.", severity="info")
    except IntegrationRequestError as exc:
        add_check("base_url", False, str(exc))

    auth_ok, auth_message = _preflight_auth(source)
    add_check("credentials", auth_ok, auth_message if not auth_ok else "Las credenciales están configuradas.")

    products_endpoint = _endpoint_config(source, "products")
    inventory_endpoint = _endpoint_config(source, "inventory")
    products_path = products_endpoint.get("path")
    inventory_path = inventory_endpoint.get("path")
    add_check(
        "catalog_endpoint",
        bool(products_path),
        "Configura el endpoint de productos antes de sincronizar." if not products_path else "Endpoint de catálogo configurado.",
    )

    preview: dict[str, Any]
    try:
        preview = await preview_source(source)
    except (IntegrationRequestError, TypeError, ValueError) as exc:
        preview = {"products": {}, "inventory": None, "errors": [str(exc)]}
    product_preview = preview.get("products") or {}
    product_samples = product_preview.get("mapped") or []
    valid_product_samples = [
        item for item in product_samples
        if item.get("external_id") not in (None, "") and item.get("name") not in (None, "")
    ]
    if product_preview.get("available") and product_preview.get("received_count", 0) > 0:
        add_check(
            "catalog_response",
            True,
            f"El catálogo respondió con {product_preview['received_count']} registro(s) de muestra.",
            severity="info",
            sample_count=product_preview.get("received_count", 0),
        )
        add_check(
            "catalog_mapping",
            bool(valid_product_samples),
            "La muestra no contiene ID externo y nombre utilizables." if not valid_product_samples
            else f"El mapeo identifica {len(valid_product_samples)} registro(s) de muestra.",
            sample_count=len(valid_product_samples),
        )
    else:
        add_check(
            "catalog_response",
            False,
            "El endpoint de catálogo no devolvió registros utilizables.",
        )

    catalog_external_ids = {
        str(item.get("external_id")).strip()
        for item in valid_product_samples
        if item.get("external_id") not in (None, "")
    }
    linked_sample_ids: set[str] = set()
    if catalog_external_ids:
        linked_rows = (await db.execute(
            select(IntegrationRecordLink.external_id).where(
                IntegrationRecordLink.source_id == source.id,
                IntegrationRecordLink.entity_type == "product",
                IntegrationRecordLink.external_id.in_(catalog_external_ids),
            )
        )).scalars().all()
        linked_sample_ids = {str(value) for value in linked_rows}
    add_check(
        "catalog_links",
        True,
        "La muestra corresponde a un catálogo nuevo; se crearán los vínculos al importar." if not linked_sample_ids
        else f"{len(linked_sample_ids)} registro(s) de la muestra ya tienen vínculo local.",
        severity="info",
        linked_count=len(linked_sample_ids),
    )

    catalog_summary = {
        "endpoint_configured": bool(products_path),
        "sample_count": product_preview.get("received_count", 0),
        "mapped_count": len(valid_product_samples),
        "linked_count": len(linked_sample_ids),
    }

    inventory_summary = {
        "endpoint_configured": bool(inventory_path),
        "batch_enabled": bool(_inventory_batch_config(inventory_endpoint)),
        "sample_count": 0,
        "mapped_count": 0,
    }
    if inventory_path:
        branch, warehouse = await _resolve_inventory_location(db, source)
        add_check(
            "inventory_location",
            bool(branch),
            "La empresa no tiene una sucursal activa para guardar existencias." if not branch
            else f"Sucursal de inventario lista: {branch.name}.",
            warehouse_configured=bool(warehouse),
        )
        batch_config = _inventory_batch_config(inventory_endpoint)
        if batch_config:
            sku_result = await db.execute(
                select(IntegrationRecordLink.external_sku).where(
                    IntegrationRecordLink.source_id == source.id,
                    IntegrationRecordLink.entity_type.in_(["product", "variant"]),
                    IntegrationRecordLink.external_sku.is_not(None),
                ).limit(1)
            )
            has_linked_sku = sku_result.scalars().first() is not None
            if not has_linked_sku:
                add_check(
                    "inventory_catalog_dependency",
                    False,
                    "El inventario por lotes necesita primero una sincronización de catálogo con SKU vinculados.",
                    severity="warning",
                )
            else:
                add_check(
                    "inventory_batch",
                    True,
                    f"Inventario por lotes configurado (máximo {batch_config['size']} SKU por petición).",
                    severity="info",
                )
        inventory_preview = preview.get("inventory") or {}
        inventory_samples = inventory_preview.get("mapped") or []
        valid_inventory_samples = [
            item for item in inventory_samples
            if (item.get("external_id") not in (None, "") or item.get("sku") not in (None, ""))
            and item.get("quantity") is not None
        ]
        inventory_summary.update({
            "sample_count": inventory_preview.get("received_count", 0),
            "mapped_count": len(valid_inventory_samples),
        })
        if batch_config and not inventory_preview.get("available") and not inventory_preview.get("received_count"):
            # A batch endpoint cannot be previewed until there are local SKUs;
            # this is a warning above, not a false provider failure.
            pass
        elif inventory_preview.get("available"):
            add_check(
                "inventory_mapping",
                bool(valid_inventory_samples),
                "La muestra de inventario no contiene identificador y cantidad válidos." if not valid_inventory_samples
                else f"El mapeo identifica {len(valid_inventory_samples)} registro(s) de inventario.",
                sample_count=len(valid_inventory_samples),
            )
        elif inventory_preview.get("error"):
            add_check("inventory_response", False, str(inventory_preview["error"]))
    else:
        add_check(
            "inventory_endpoint",
            True,
            "No hay endpoint de inventario; el origen solo sincronizará catálogo.",
            severity="warning",
        )

    # Network/configuration errors already have a useful provider message in
    # the preview. Keep the response compact and avoid returning raw payloads.
    for preview_error in preview.get("errors") or []:
        if preview_error not in errors and "No hay SKU" not in preview_error:
            errors.append(str(preview_error))

    return {
        "source_id": source.id,
        "success": not errors,
        "message": "Origen compatible para sincronizar." if not errors else "El origen requiere correcciones antes de sincronizar.",
        "checks": checks,
        "warnings": warnings,
        "errors": errors,
        "catalog": catalog_summary,
        "inventory": inventory_summary,
    }


async def _fetch_entity(
    source: IntegrationSource,
    entity: str,
    progress_callback: ProgressCallback | None = None,
) -> list[dict[str, Any]]:
    endpoint = _endpoint_config(source, entity)
    path = endpoint.get("path")
    if not path:
        return []
    url = _url_for(source, str(path))
    headers = _build_headers(source)
    pagination = _pagination_config(endpoint)
    entity_label = "catálogo" if entity == "products" else "inventario"
    if not pagination.get("enabled", False):
        await _report_progress(
            progress_callback,
            stage="FETCHING",
            message=f"Consultando {entity_label}...",
            percent=10,
            current=0,
            total=1,
            entity=entity,
            page=1,
            pages_total=1,
        )
        status_code, payload = await _request_json(url, headers)
        rows = _extract_entity_rows(payload, endpoint, entity, status_code)
        await _report_progress(
            progress_callback,
            stage="FETCHING",
            message=f"Datos de {entity_label} recibidos.",
            percent=40,
            current=1,
            total=1,
            entity=entity,
            page=1,
            pages_total=1,
            items_received=len(rows),
        )
        return rows

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

        metadata = payload.get("meta") if isinstance(payload, dict) else None
        pages_total_value = (
            metadata.get("pages") or metadata.get("last_page")
            if isinstance(metadata, dict)
            else None
        )
        total_items_value = (
            metadata.get("total") or metadata.get("count")
            if isinstance(metadata, dict)
            else None
        )
        pages_total = int(_as_float(pages_total_value) or 0) or None
        total_items = int(_as_float(total_items_value) or 0) or None
        progress_total = pages_total or max_pages
        progress_percent = 10 + int(30 * min(page, progress_total) / progress_total)
        await _report_progress(
            progress_callback,
            stage="FETCHING",
            message=f"Descargando {entity_label}: página {page}{f' de {pages_total}' if pages_total else ''}.",
            percent=progress_percent,
            current=page,
            total=pages_total,
            entity=entity,
            page=page,
            pages_total=pages_total,
            items_received=len(all_items),
            items_total=total_items,
        )

        if not page_items:
            break
        next_value = _value(payload, pagination.get("next_path")) if pagination.get("next_path") else None
        if pagination.get("next_path") and not next_value:
            break
        if pages_total is not None and page >= pages_total:
            break
        if total_items is not None and len(all_items) >= total_items:
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

    await _report_progress(
        progress_callback,
        stage="FETCHING",
        message=f"Datos de {entity_label} recibidos: {len(all_items)} registros.",
        percent=40,
        current=pages_total or page,
        total=pages_total,
        entity=entity,
        page=page,
        pages_total=pages_total,
        items_received=len(all_items),
        items_total=total_items,
    )
    return all_items


async def _inventory_sku_values(
    db: AsyncSession,
    source: IntegrationSource,
    external_products: dict[str, Product] | None = None,
    external_variants: dict[str, ProductVariant] | None = None,
) -> list[str]:
    """Collect the external SKU values that the provider can resolve.

    A catalog/full sync already has the links in memory. For an inventory-only
    run, read the persisted integration links so the request remains bounded to
    products previously imported from this source.
    """

    values: set[str] = set()
    for lookup in (external_products or {}, external_variants or {}):
        for key in lookup:
            if key.startswith("sku:"):
                sku = key.removeprefix("sku:").strip()
                if sku:
                    values.add(sku)
    if values:
        return sorted(values)

    result = await db.execute(
        select(IntegrationRecordLink.external_sku).where(
            IntegrationRecordLink.source_id == source.id,
            IntegrationRecordLink.entity_type.in_(["product", "variant"]),
            IntegrationRecordLink.external_sku.is_not(None),
        )
    )
    return sorted({str(sku).strip() for sku in result.scalars().all() if sku not in (None, "") and str(sku).strip()})


async def _fetch_inventory(
    db: AsyncSession,
    source: IntegrationSource,
    external_products: dict[str, Product] | None = None,
    external_variants: dict[str, ProductVariant] | None = None,
    progress_callback: ProgressCallback | None = None,
) -> list[dict[str, Any]]:
    """Fetch inventory, optionally splitting SKU values into provider-sized batches."""

    endpoint = _endpoint_config(source, "inventory")
    batch = _inventory_batch_config(endpoint)
    if not batch:
        return await _fetch_entity(source, "inventory", progress_callback)

    path = endpoint.get("path")
    if not path:
        return []
    sku_values = await _inventory_sku_values(db, source, external_products, external_variants)
    if not sku_values:
        await _report_progress(
            progress_callback,
            stage="FETCHING",
            message="No hay SKU importados para consultar el inventario.",
            percent=40,
            current=0,
            total=0,
            entity="inventory",
            items_received=0,
            items_total=0,
        )
        return []

    url = _url_for(source, str(path))
    headers = _build_headers(source)
    batch_size = int(batch["size"])
    sku_batches = [sku_values[index : index + batch_size] for index in range(0, len(sku_values), batch_size)]
    all_items: list[dict[str, Any]] = []
    total_batches = len(sku_batches)
    for batch_index, sku_batch in enumerate(sku_batches, start=1):
        batch_url = _url_with_query(url, {str(batch["query_param"]): ",".join(sku_batch)})
        status_code, payload = await _request_json(batch_url, headers)
        rows = _extract_entity_rows(payload, endpoint, "inventory", status_code)
        all_items.extend(rows)
        await _report_progress(
            progress_callback,
            stage="FETCHING",
            message=f"Descargando inventario: lote {batch_index} de {total_batches} ({len(sku_batch)} SKU).",
            percent=10 + int(30 * batch_index / total_batches),
            current=batch_index,
            total=total_batches,
            entity="inventory",
            page=batch_index,
            pages_total=total_batches,
            items_received=len(all_items),
            items_total=len(sku_values),
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
    progress_callback: ProgressCallback | None = None,
) -> list[dict[str, Any]]:
    """Read stock embedded in the catalog without modifying catalog records."""
    items = await _fetch_entity(source, "products", progress_callback)
    mapping = _field_map(source)
    collections = (source.configuration or {}).get("collections") or {}
    variants_path = collections.get("variants_path") or "variants[]"
    variants_prefix = str(variants_path)
    if not variants_prefix.endswith("[]"):
        variants_prefix = f"{variants_prefix}[]"
    embedded_inventory: list[dict[str, Any]] = []

    for item in items:
        external_id_value = _mapped(
            item,
            mapping,
            "product.external_id",
            "id",
            "external_id",
            "uuid",
            "product_id",
        )
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
    db: AsyncSession,
    source: IntegrationSource,
    run: IntegrationSyncRun,
    progress_callback: ProgressCallback | None = None,
) -> tuple[dict[str, Product], dict[str, ProductVariant], list[dict[str, Any]]]:
    items = await _fetch_entity(source, "products", progress_callback)
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

    await _report_progress(
        progress_callback,
        stage="PROCESSING",
        message=f"Procesando catálogo: 0 de {len(items)} registros.",
        percent=45,
        current=0,
        total=len(items),
        entity="products",
        items_received=len(items),
        items_total=len(items),
        items_failed=run.items_failed,
        created=run.products_created,
        updated=run.products_updated,
    )

    async def report_processed(index: int) -> None:
        if index != len(items) and index % 25 != 0:
            return
        await _report_progress(
            progress_callback,
            stage="PROCESSING",
            message=f"Procesando catálogo: {index} de {len(items)} registros.",
            percent=45 + int(50 * index / max(1, len(items))),
            current=index,
            total=len(items),
            entity="products",
            items_received=len(items),
            items_total=len(items),
            items_failed=run.items_failed,
            created=run.products_created,
            updated=run.products_updated,
        )

    for index, item in enumerate(items, start=1):
        external_id = str(
            _mapped(item, mapping, "product.external_id", "id", "external_id", "uuid", "product_id") or ""
        ).strip()
        name = str(_mapped(item, mapping, "product.name", "name", "title", "product_name") or "").strip()
        if not external_id or not name:
            run.items_failed += 1
            _record_sync_item_error(
                run,
                "catalog_missing_identity",
                external_id=external_id,
                name=name,
                sku=_mapped(item, mapping, "product.sku", "sku", "code", "reference"),
            )
            await report_processed(index)
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
        # A later catalog sync is the explicit path for restoring an archived
        # product after a catalog purge.
        product.is_active = True
        # Imported catalog products are sellable and purchasable by default.
        # A provider value, when explicitly mapped, is applied below and can
        # override these defaults.
        product.sale_ok = True
        product.purchase_ok = True
        if sku is not None:
            product.sku = sku
        for field, key, *fallbacks in [
            ("description", "product.description", "description", "body_html"),
            ("image_url", "product.image_url", "image_url", "image"),
            ("barcode", "product.barcode", "barcode", "ean"),
            ("internal_reference", "product.internal_reference", "internal_reference", "internal_code", "codigo_interno"),
        ]:
            value = _mapped(item, mapping, key, *fallbacks)
            if value not in (None, ""):
                if field == "image_url":
                    # Apply the configured asset base to relative values from
                    # providers.  Without this, the product's primary image
                    # bypassed ``asset_base_url`` while gallery images used it.
                    value = _asset_url(source, value)
                setattr(product, field, str(value))
        for field, key, *fallbacks in [
            ("price", "product.price", "price", "sale_price"),
            ("cost", "product.cost", "cost", "purchase_price"),
            ("weight", "product.weight", "weight", "weight_kg", "product_weight", "peso", "peso_kg"),
            ("volume", "product.volume", "volume", "volume_l", "product_volume", "volumen", "volumen_l"),
            ("tax_rate", "product.tax_rate", "tax_rate", "tax", "vat", "iva", "impuesto"),
            ("min_stock", "product.min_stock", "min_stock", "minimum_stock", "reorder_point", "stock_minimo"),
        ]:
            value = _as_float(_mapped(item, mapping, key, *fallbacks))
            if value is not None:
                setattr(product, field, value)

        for field, key, *fallbacks in [
            ("track_inventory", "product.track_inventory", "track_inventory", "manage_stock", "inventory_tracked", "control_inventario"),
            ("sale_ok", "product.sale_ok", "sale_ok", "sellable", "can_sell", "allow_sale"),
            ("purchase_ok", "product.purchase_ok", "purchase_ok", "purchasable", "can_purchase", "allow_purchase"),
        ]:
            value = _as_bool(_mapped(item, mapping, key, *fallbacks))
            if value is not None:
                setattr(product, field, value)

        product_type = _as_choice(
            _mapped(item, mapping, "product.product_type", "product_type", "product_kind", "kind", "tipo_producto"),
            {"STORABLE", "CONSUMABLE", "SERVICE"},
        )
        if product_type:
            product.product_type = product_type
        tracking_type = _as_choice(
            _mapped(item, mapping, "product.tracking_type", "tracking_type", "tracking", "tipo_seguimiento"),
            {"NONE", "LOT", "SERIAL"},
        )
        if tracking_type:
            product.tracking_type = tracking_type

        unit_name = _mapped(
            item,
            mapping,
            "product.unit.name",
            "unit_name",
            "unit_of_measure",
            "uom",
            "unidad",
            "unidad_medida",
            "unit",
        )
        purchase_unit_name = _mapped(
            item,
            mapping,
            "product.purchase_unit.name",
            "purchase_unit_name",
            "purchase_uom",
            "unidad_compra",
            "unidad_compra_nombre",
        )
        unit = await _sync_unit_of_measure(db, source, unit_name)
        purchase_unit = await _sync_unit_of_measure(db, source, purchase_unit_name)
        if unit:
            product.unit_of_measure_id = unit.id
        if purchase_unit:
            product.purchase_uom_id = purchase_unit.id

        product_attributes = _collect_product_attributes(item, mapping)
        category_external_id = _mapped(item, mapping, "product.category.external_id", "category_id", "category_external_id")
        category_name = _mapped(
            item,
            mapping,
            "product.category.name",
            "category_name",
            "category",
            "categoria",
            "nombre_categoria",
        )
        brand_external_id = _mapped(
            item,
            mapping,
            "product.brand.external_id",
            "brand_id",
            "brand_external_id",
            "brand_code",
            "manufacturer_id",
            "marca_id",
        )
        brand_name = _mapped(
            item,
            mapping,
            "product.brand.name",
            "brand_name",
            "brand",
            "brand_title",
            "manufacturer",
            "manufacturer_name",
            "marca",
            "nombre_marca",
        )
        supplier_external_id = _mapped(item, mapping, "product.supplier.external_id", "provider_id", "supplier_id")
        supplier_name = _mapped(item, mapping, "product.supplier.name", "provider_name", "supplier_name")
        brand = await _sync_brand(db, source, brand_external_id, brand_name)
        if brand:
            product.brand_id = brand.id
        supplier = await _sync_supplier(db, source, supplier_external_id, supplier_name)
        if supplier:
            product.supplier_id = supplier.id
        category_external_text = _as_text(category_external_id, "id", "code", "value")
        if category_external_text not in (None, ""):
            product_attributes["external_category_id"] = category_external_text
        if category_name not in (None, ""):
            category_text = _as_text(category_name, "name", "title", "label")
            product.category_id = await _sync_category(db, source, category_text)
            if category_text:
                product_attributes["category_name"] = category_text
        brand_external_text = _as_text(brand_external_id, "id", "code", "value")
        brand_name_text = _as_text(brand_name, "name", "title", "label", "value")
        if brand_external_text not in (None, ""):
            product_attributes["external_brand_id"] = brand_external_text
        if brand_name_text not in (None, ""):
            product_attributes["brand_name"] = brand_name_text
        supplier_external_text = _as_text(supplier_external_id, "id", "code", "value")
        supplier_name_text = _as_text(supplier_name, "name", "title", "label", "value")
        if supplier_external_text not in (None, ""):
            product_attributes["external_supplier_id"] = supplier_external_text
        if supplier_name_text not in (None, ""):
            product_attributes["supplier_name"] = supplier_name_text
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
        link.is_active = True
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
                _record_sync_item_error(
                    run,
                    "variant_missing_identity",
                    product_external_id=external_id,
                    variant_sku=_mapped_context(
                        variant_item, mapping, "variant.sku", variants_prefix, "sku", "code", "reference"
                    ),
                )
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

            # A catalog purge archives the product and its variants when
            # business history protects them from physical deletion. A later
            # catalog sync is the explicit source-of-truth path for restoring
            # both records so the imported catalog is usable again.
            variant.is_active = True

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
            variant_link.is_active = True
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

        await report_processed(index)

    return external_products, external_variants, embedded_inventory


async def _sync_inventory(
    db: AsyncSession,
    source: IntegrationSource,
    run: IntegrationSyncRun,
    external_products: dict[str, Product] | None = None,
    external_variants: dict[str, ProductVariant] | None = None,
    embedded_inventory: list[dict[str, Any]] | None = None,
    progress_callback: ProgressCallback | None = None,
) -> None:
    external_products = external_products or {}
    external_variants = external_variants or {}
    items = await _fetch_inventory(
        db,
        source,
        external_products,
        external_variants,
        progress_callback,
    )
    if embedded_inventory is None:
        embedded_inventory = []
        if not _endpoint_config(source, "inventory").get("path"):
            embedded_inventory = await _load_embedded_inventory(db, source, run, progress_callback)
    if not items and not embedded_inventory:
        run.details = {**(run.details or {}), "inventory_message": "El origen no devolvió existencias."}
        await _report_progress(
            progress_callback,
            stage="PROCESSING",
            message="El origen no devolvió existencias.",
            percent=100,
            current=0,
            total=0,
            entity="inventory",
            items_received=0,
            items_total=0,
            items_failed=run.items_failed,
            updated=run.inventory_updated,
        )
        return
    branch, warehouse = await _resolve_inventory_location(db, source)
    if not branch:
        run.items_failed += len(items) + len(embedded_inventory)
        run.details = {**(run.details or {}), "inventory_error": "La empresa no tiene una sucursal activa."}
        _record_sync_item_error(
            run,
            "branch_not_configured",
            records=len(items) + len(embedded_inventory),
        )
        return

    mapping = _field_map(source)
    run.inventory_processed = len(items) + len(embedded_inventory)
    inventory_total = run.inventory_processed
    inventory_current = 0
    await _report_progress(
        progress_callback,
        stage="PROCESSING",
        message=f"Procesando inventario: 0 de {inventory_total} registros.",
        percent=45,
        current=0,
        total=inventory_total,
        entity="inventory",
        items_received=inventory_total,
        items_total=inventory_total,
        items_failed=run.items_failed,
        updated=run.inventory_updated,
    )

    async def report_inventory_processed() -> None:
        if inventory_current != inventory_total and inventory_current % 25 != 0:
            return
        await _report_progress(
            progress_callback,
            stage="PROCESSING",
            message=f"Procesando inventario: {inventory_current} de {inventory_total} registros.",
            percent=45 + int(50 * inventory_current / max(1, inventory_total)),
            current=inventory_current,
            total=inventory_total,
            entity="inventory",
            items_received=inventory_total,
            items_total=inventory_total,
            items_failed=run.items_failed,
            updated=run.inventory_updated,
        )
    inventory_cache: dict[tuple[Any, Any, Any, Any, Any], Inventory] = {}
    warehouse_id = warehouse.id if warehouse else None

    async def upsert_inventory(
        product: Product, variant: ProductVariant | None, quantity: float
    ) -> bool:
        # Provider snapshots are physical stock, never a negative adjustment.
        # Clamp malformed values before persisting them or exposing them to the
        # storefront and checkout availability calculations.
        quantity = max(0.0, float(quantity))
        cache_key = (source.company_id, product.id, branch.id, warehouse_id, variant.id if variant else None)
        cached_inventory = inventory_cache.get(cache_key)
        if cached_inventory:
            previous_stock = float(cached_inventory.quantity or 0)
            reserved_quantity = float(cached_inventory.reserved_quantity or 0)
            if quantity < reserved_quantity:
                return False
            cached_inventory.quantity = quantity
            if abs(quantity - previous_stock) > 1e-9:
                db.add(InventoryMovement(
                    id=uuid.uuid4(),
                    company_id=source.company_id,
                    product_id=product.id,
                    variant_id=variant.id if variant else None,
                    branch_id=branch.id,
                    warehouse_id=warehouse_id,
                    type=MovementType.ADJ,
                    quantity=quantity - previous_stock,
                    previous_stock=previous_stock,
                    new_stock=quantity,
                    reference_id=str(getattr(run, "id", "")) or None,
                    reason="Sincronización de inventario externa",
                ))
            run.inventory_updated += 1
            return True
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
        previous_stock = float(inventory.quantity or 0)
        reserved_quantity = float(inventory.reserved_quantity or 0)
        if quantity < reserved_quantity:
            return False
        inventory.quantity = quantity
        if abs(quantity - previous_stock) > 1e-9:
            db.add(InventoryMovement(
                id=uuid.uuid4(),
                company_id=source.company_id,
                product_id=product.id,
                variant_id=variant.id if variant else None,
                branch_id=branch.id,
                warehouse_id=warehouse_id,
                type=MovementType.ADJ,
                quantity=quantity - previous_stock,
                previous_stock=previous_stock,
                new_stock=quantity,
                reference_id=str(getattr(run, "id", "")) or None,
                reason="Sincronización de inventario externa",
            ))
        run.inventory_updated += 1
        return True

    for embedded in embedded_inventory:
        updated = await upsert_inventory(embedded["product"], embedded.get("variant"), embedded["quantity"])
        if not updated:
            run.items_failed += 1
            _record_sync_item_error(
                run,
                "stock_below_reserved",
                sku=embedded.get("sku"),
                quantity=embedded.get("quantity"),
            )
        inventory_current += 1
        await report_inventory_processed()

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
        if not product:
            run.items_failed += 1
            _record_sync_item_error(
                run,
                "product_not_found",
                external_id=external_id,
                sku=sku,
                variant_sku=variant_sku,
            )
            inventory_current += 1
            await report_inventory_processed()
            continue
        if product.company_id != source.company_id:
            run.items_failed += 1
            _record_sync_item_error(
                run,
                "company_mismatch",
                external_id=external_id,
                sku=sku,
            )
            inventory_current += 1
            await report_inventory_processed()
            continue
        if quantity is None:
            run.items_failed += 1
            _record_sync_item_error(
                run,
                "quantity_invalid",
                external_id=external_id,
                sku=sku,
            )
            inventory_current += 1
            await report_inventory_processed()
            continue
        if not await upsert_inventory(product, variant, quantity):
            run.items_failed += 1
            _record_sync_item_error(
                run,
                "stock_below_reserved",
                external_id=external_id,
                sku=sku,
                quantity=quantity,
            )
        inventory_current += 1
        await report_inventory_processed()


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

    async def persist_progress(progress: dict[str, Any]) -> None:
        run.details = {**(run.details or {}), "progress": progress}
        try:
            async with SessionLocal() as progress_db:
                await progress_db.execute(
                    update(IntegrationSyncRun)
                    .where(IntegrationSyncRun.id == run_id)
                    .values(details=run.details)
                )
                await progress_db.commit()
        except Exception:  # noqa: BLE001 - progress must never stop the sync
            return

    try:
        validate_source(source)
        await _report_progress(
            persist_progress,
            stage="STARTING",
            message="Preparando la sincronización...",
            percent=2,
            current=0,
            entity=run.sync_type.lower(),
        )

        # Progress is persisted through a short-lived session so the UI can
        # observe a long-running sync. Detach the run before processing starts:
        # the catalog/inventory transaction flushes products and variants in
        # batches, and keeping the run entity attached would lock its row until
        # the whole sync commits. The progress session would then wait forever
        # on that row while this transaction waits for the progress callback.
        # The run is merged back into the main session once processing finishes.
        db.expunge(run)

        if run.sync_type in {"CATALOG", "FULL"}:
            products, variants, embedded_inventory = await _sync_products(
                db, source, run, persist_progress
            )
        else:
            products, variants, embedded_inventory = {}, {}, None
        if run.sync_type in {"INVENTORY", "FULL"}:
            await _sync_inventory(
                db, source, run, products, variants, embedded_inventory, persist_progress
            )
        run.status = "PARTIAL" if run.items_failed else "SUCCESS"
        run.finished_at = datetime.utcnow()
        run.details = {
            **(run.details or {}),
            "progress": {
                "stage": "COMPLETED",
                "message": "Sincronización completada." if run.status == "SUCCESS" else "Sincronización completada con alertas.",
                "percent": 100,
                "current": run.products_processed or run.inventory_processed,
                "total": run.products_processed or run.inventory_processed,
                "items_failed": run.items_failed,
                "created": run.products_created,
                "updated": run.products_updated or run.inventory_updated,
            },
        }
        await db.merge(run)
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
            failed_run.details = {
                **(failed_run.details or {}),
                "progress": {
                    "stage": "FAILED",
                    "message": "La sincronización falló.",
                    "percent": 100,
                    "current": failed_run.products_processed or failed_run.inventory_processed,
                    "total": failed_run.products_processed or failed_run.inventory_processed,
                    "items_failed": failed_run.items_failed,
                    "created": failed_run.products_created,
                    "updated": failed_run.products_updated or failed_run.inventory_updated,
                },
            }
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
