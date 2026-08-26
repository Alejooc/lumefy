"""Validation and compatibility helpers for visual storefront themes."""

from __future__ import annotations

from copy import deepcopy
import json
import re
from typing import Any


HOME_SECTION_REGISTRY: tuple[dict[str, Any], ...] = (
    {
        "type": "hero",
        "label": "Hero y promociones",
        "description": "Mensaje principal y promociones destacadas.",
        "icon": "sparkles",
    },
    {
        "type": "categories",
        "label": "Categorías",
        "description": "Accesos visuales a colecciones y categorías.",
        "icon": "grid",
    },
    {
        "type": "new_arrivals",
        "label": "Novedades",
        "description": "Productos publicados recientemente.",
        "icon": "star",
    },
    {
        "type": "promo_banners",
        "label": "Banners editoriales",
        "description": "Mensajes y campañas de la tienda.",
        "icon": "megaphone",
    },
    {
        "type": "best_sellers",
        "label": "Productos destacados",
        "description": "Los productos que quieres priorizar.",
        "icon": "trending-up",
    },
    {
        "type": "countdown",
        "label": "Cuenta regresiva",
        "description": "Promoción con fecha de finalización.",
        "icon": "clock",
    },
    {
        "type": "testimonials",
        "label": "Testimonios",
        "description": "Historias y reseñas de clientes.",
        "icon": "quote",
    },
    {
        "type": "newsletter",
        "label": "Newsletter",
        "description": "Captura suscripciones y novedades.",
        "icon": "mail",
    },
    {
        "type": "closing_cta",
        "label": "Llamado final",
        "description": "Cierre de página con una acción principal.",
        "icon": "arrow-right",
    },
)

_SECTION_TYPES = {item["type"] for item in HOME_SECTION_REGISTRY}
_ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9_-]{0,63}$")
_TEMPLATE_PATTERN = re.compile(r"^[a-z0-9][a-z0-9_-]{0,79}$")
_FORBIDDEN_KEYS = {
    "__proto__",
    "prototype",
    "constructor",
    "dangerouslysetinnerhtml",
    "html",
    "raw_html",
    "script",
    "javascript",
    "raw_css",
    "iframe",
}
_FORBIDDEN_TAG = re.compile(r"<\s*/?\s*(?:script|iframe|object|embed|style|form)\b", re.IGNORECASE)
_FORBIDDEN_PROTOCOL = re.compile(r"^\s*(?:javascript|vbscript|data):", re.IGNORECASE)
_EVENT_HANDLER_KEY = re.compile(r"^on[a-z][a-z0-9_:-]*$", re.IGNORECASE)
MAX_DOCUMENT_BYTES = 512_000


def _validate_safe_value(value: Any, path: str = "document", depth: int = 0) -> None:
    """Reject executable markup and pathological payloads before persistence."""
    if depth > 12:
        raise ValueError("El documento visual tiene demasiados niveles anidados")
    if isinstance(value, dict):
        if len(value) > 2000:
            raise ValueError(f"{path} tiene demasiadas propiedades")
        for key, item in value.items():
            normalized_key = str(key).strip().lower()
            if normalized_key in _FORBIDDEN_KEYS or _EVENT_HANDLER_KEY.fullmatch(normalized_key):
                raise ValueError(f"La propiedad {key} no está permitida en el documento visual")
            _validate_safe_value(item, f"{path}.{key}", depth + 1)
        return
    if isinstance(value, list):
        if len(value) > 200:
            raise ValueError(f"{path} supera el límite de elementos")
        for index, item in enumerate(value):
            _validate_safe_value(item, f"{path}[{index}]", depth + 1)
        return
    if isinstance(value, str):
        if len(value) > 20_000:
            raise ValueError(f"{path} supera el límite de texto")
        if _FORBIDDEN_TAG.search(value) or _FORBIDDEN_PROTOCOL.match(value):
            raise ValueError(f"{path} contiene contenido no permitido")


def _validate_document_size(document: dict[str, Any]) -> None:
    try:
        size = len(json.dumps(document, ensure_ascii=False, separators=(",", ":")))
    except (TypeError, ValueError) as exc:
        raise ValueError("El documento visual contiene valores no serializables") from exc
    if size > MAX_DOCUMENT_BYTES:
        raise ValueError("El documento visual supera el tamaño máximo permitido")


def _legacy_home(theme_settings: Any) -> dict[str, Any]:
    if not isinstance(theme_settings, dict):
        return {}
    value = theme_settings.get("home")
    return deepcopy(value) if isinstance(value, dict) else {}


def _default_sections() -> list[dict[str, Any]]:
    return [
        {
            "id": item["type"],
            "type": item["type"],
            "enabled": True,
            "settings": {},
            "blocks": [],
        }
        for item in HOME_SECTION_REGISTRY
    ]


def build_home_document(theme_settings: Any = None) -> dict[str, Any]:
    """Create a visual document while preserving the current home payload."""
    return {
        "schema_version": 1,
        "template": "home",
        "settings": {},
        "legacy_home": _legacy_home(theme_settings),
        "sections": _default_sections(),
    }


def _normalize_section(raw: Any, index: int) -> dict[str, Any] | None:
    if not isinstance(raw, dict):
        return None
    section_type = str(raw.get("type") or "").strip().lower()
    if section_type not in _SECTION_TYPES:
        raise ValueError(f"Sección no permitida: {section_type or 'sin tipo'}")

    raw_id = str(raw.get("id") or section_type).strip().lower()
    if not _ID_PATTERN.fullmatch(raw_id):
        raise ValueError(f"ID de sección inválido en la posición {index + 1}")

    settings = raw.get("settings")
    if settings is None:
        settings = {}
    if not isinstance(settings, dict):
        raise ValueError(f"La configuración de {raw_id} debe ser un objeto")

    blocks = raw.get("blocks")
    if blocks is None:
        blocks = []
    if not isinstance(blocks, list):
        raise ValueError(f"Los bloques de {raw_id} deben ser una lista")
    if len(blocks) > 50:
        raise ValueError(f"La sección {raw_id} supera el límite de 50 bloques")
    if any(not isinstance(block, dict) for block in blocks):
        raise ValueError(f"Los bloques de {raw_id} deben ser objetos")

    return {
        "id": raw_id,
        "type": section_type,
        "enabled": raw.get("enabled") is not False,
        "settings": deepcopy(settings),
        "blocks": deepcopy(blocks),
    }


def normalize_home_document(document: Any, theme_settings: Any = None) -> dict[str, Any]:
    """Validate a submitted document and fill legacy-compatible defaults."""
    if not isinstance(document, dict):
        raise ValueError("El documento visual debe ser un objeto")
    _validate_safe_value(document)
    _validate_document_size(document)

    template = str(document.get("template") or "home").strip().lower()
    if template != "home":
        raise ValueError("Solo se puede editar la plantilla home en esta versión")

    raw_sections = document.get("sections")
    if raw_sections is None or raw_sections == []:
        sections = _default_sections()
    elif not isinstance(raw_sections, list):
        raise ValueError("Las secciones deben ser una lista")
    else:
        if len(raw_sections) > 20:
            raise ValueError("El inicio no puede tener más de 20 secciones")
        sections = []
        seen_ids: set[str] = set()
        for index, raw_section in enumerate(raw_sections):
            section = _normalize_section(raw_section, index)
            if section is None:
                raise ValueError(f"Sección inválida en la posición {index + 1}")
            if section["id"] in seen_ids:
                raise ValueError(f"ID de sección repetido: {section['id']}")
            seen_ids.add(section["id"])
            sections.append(section)

    settings = document.get("settings")
    if settings is None:
        settings = {}
    if not isinstance(settings, dict):
        raise ValueError("La configuración global debe ser un objeto")

    legacy_home = document.get("legacy_home")
    if not isinstance(legacy_home, dict):
        legacy_home = _legacy_home(theme_settings)

    return {
        "schema_version": 1,
        "template": "home",
        "settings": deepcopy(settings),
        "legacy_home": deepcopy(legacy_home),
        "sections": sections,
    }


def component_registry() -> list[dict[str, Any]]:
    return deepcopy(list(HOME_SECTION_REGISTRY))


def validate_template_key(template_key: str) -> str:
    value = (template_key or "").strip().lower()
    if not _TEMPLATE_PATTERN.fullmatch(value):
        raise ValueError("La plantilla solicitada no es válida")
    if value != "home":
        raise ValueError("La plantilla solicitada aún no está disponible")
    return value
