"""Validation and compatibility helpers for visual storefront themes."""

from __future__ import annotations

from copy import deepcopy
from html import escape
from html.parser import HTMLParser
import json
import re
from typing import Any
from urllib.parse import urlsplit


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
    {
        "type": "custom_embed",
        "label": "Código personalizado",
        "description": "Contenido HTML seguro o integraciones externas.",
        "icon": "code",
    },
)

_SECTION_TYPES = {item["type"] for item in HOME_SECTION_REGISTRY}
_DEFAULT_SECTION_TYPES = _SECTION_TYPES - {"custom_embed"}
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
_HEX_COLOR = re.compile(r"^#[0-9a-f]{6}$", re.IGNORECASE)
MAX_DOCUMENT_BYTES = 512_000

_CUSTOM_HTML_ALLOWED_TAGS = {
    "a",
    "abbr",
    "b",
    "blockquote",
    "br",
    "code",
    "div",
    "em",
    "h1",
    "h2",
    "h3",
    "h4",
    "h5",
    "h6",
    "hr",
    "i",
    "img",
    "li",
    "ol",
    "p",
    "pre",
    "small",
    "span",
    "strong",
    "sub",
    "sup",
    "u",
    "ul",
}
_CUSTOM_HTML_VOID_TAGS = {"br", "hr", "img"}
_CUSTOM_HTML_BLOCKED_TAGS = {"embed", "form", "iframe", "object", "script", "style"}
_CUSTOM_HTML_GLOBAL_ATTRIBUTES = {"aria-label", "class", "id", "role", "title"}
_CUSTOM_HTML_ATTRIBUTES = {
    "a": {"href", "rel", "target"},
    "img": {"alt", "height", "loading", "src", "width"},
}
_CUSTOM_HTML_URL_ATTRIBUTES = {"href", "src"}


def _safe_content_url(value: str, *, allow_mailto: bool = False) -> str:
    """Allow links and images without executable or protocol-relative URLs."""
    candidate = value.strip()
    if not candidate or candidate.startswith("//"):
        return ""
    if candidate.startswith(("/", "#", "?")):
        return candidate

    try:
        parsed = urlsplit(candidate)
    except ValueError:
        return ""
    if parsed.username or parsed.password:
        return ""
    if parsed.scheme in {"http", "https"} and parsed.netloc:
        return candidate
    if allow_mailto and parsed.scheme == "mailto" and parsed.path:
        return candidate
    return ""


def _safe_embed_url(value: str) -> str:
    """Allow HTTPS embeds and local HTTP embeds used by the development preview."""
    candidate = value.strip()
    if not candidate:
        return ""
    try:
        parsed = urlsplit(candidate)
    except ValueError:
        return ""
    if parsed.username or parsed.password or parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return ""
    if parsed.scheme == "http":
        hostname = (parsed.hostname or "").lower().strip("[]")
        if hostname not in {"localhost", "127.0.0.1", "::1"}:
            return ""
    return candidate


class _SafeCustomHtmlParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.output: list[str] = []
        self._blocked_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        normalized_tag = tag.lower()
        if self._blocked_depth:
            if normalized_tag in _CUSTOM_HTML_BLOCKED_TAGS:
                self._blocked_depth += 1
            return
        if normalized_tag in _CUSTOM_HTML_BLOCKED_TAGS:
            self._blocked_depth = 1
            return
        if normalized_tag not in _CUSTOM_HTML_ALLOWED_TAGS:
            return

        safe_attrs: list[tuple[str, str]] = []
        allowed_attributes = _CUSTOM_HTML_GLOBAL_ATTRIBUTES | _CUSTOM_HTML_ATTRIBUTES.get(normalized_tag, set())
        for name, value in attrs:
            normalized_name = name.lower()
            if not value or normalized_name.startswith("on") or normalized_name == "style":
                continue
            if normalized_name not in allowed_attributes:
                continue
            if normalized_name in _CUSTOM_HTML_URL_ATTRIBUTES:
                value = _safe_content_url(value, allow_mailto=normalized_tag == "a" and normalized_name == "href")
                if not value:
                    continue
            safe_attrs.append((normalized_name, value))

        if normalized_tag == "a" and any(name == "target" and value == "_blank" for name, value in safe_attrs):
            if not any(name == "rel" for name, _ in safe_attrs):
                safe_attrs.append(("rel", "noopener noreferrer"))

        attributes = "".join(f' {name}="{escape(value, quote=True)}"' for name, value in safe_attrs)
        if normalized_tag in _CUSTOM_HTML_VOID_TAGS:
            self.output.append(f"<{normalized_tag}{attributes} />")
        else:
            self.output.append(f"<{normalized_tag}{attributes}>")

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.handle_starttag(tag, attrs)

    def handle_endtag(self, tag: str) -> None:
        normalized_tag = tag.lower()
        if self._blocked_depth:
            if normalized_tag in _CUSTOM_HTML_BLOCKED_TAGS:
                self._blocked_depth = max(0, self._blocked_depth - 1)
            return
        if normalized_tag in _CUSTOM_HTML_ALLOWED_TAGS and normalized_tag not in _CUSTOM_HTML_VOID_TAGS:
            self.output.append(f"</{normalized_tag}>")

    def handle_data(self, data: str) -> None:
        if not self._blocked_depth:
            self.output.append(escape(data))

    def handle_comment(self, _data: str) -> None:
        return


def _sanitize_custom_html(value: Any) -> str:
    if not isinstance(value, str) or not value.strip():
        return ""
    parser = _SafeCustomHtmlParser()
    try:
        parser.feed(value[:20_000])
        parser.close()
    except Exception:
        return ""
    return "".join(parser.output).strip()


def _normalize_custom_embed_settings(settings: dict[str, Any]) -> dict[str, Any]:
    mode = settings.get("mode") if settings.get("mode") in {"html", "iframe"} else "html"
    try:
        height = int(settings.get("iframe_height", 420))
    except (TypeError, ValueError):
        height = 420

    max_width = settings.get("max_width") if settings.get("max_width") in {"narrow", "content", "wide", "full"} else "content"
    alignment = settings.get("alignment") if settings.get("alignment") in {"left", "center", "right"} else "center"
    title = str(settings.get("iframe_title") or "Contenido integrado").strip()[:120] or "Contenido integrado"
    return {
        "mode": mode,
        "content": _sanitize_custom_html(settings.get("content")),
        "iframe_url": _safe_embed_url(str(settings.get("iframe_url") or "")),
        "iframe_title": title,
        "iframe_height": max(240, min(height, 900)),
        "max_width": max_width,
        "alignment": alignment,
    }


def _normalize_section_design(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {}

    def option(key: str, allowed: set[str], fallback: str) -> str:
        candidate = value.get(key)
        return candidate if candidate in allowed else fallback

    def color(key: str, fallback: str) -> str:
        candidate = str(value.get(key) or "").strip()
        return candidate if _HEX_COLOR.fullmatch(candidate) else fallback

    radius_value = value.get("radius")
    if radius_value == "sharp":
        radius: str | int = 0
    elif radius_value == "soft":
        radius = 16
    elif radius_value == "round":
        radius = 30
    elif radius_value == "theme":
        radius = "theme"
    else:
        try:
            radius = max(0, min(int(radius_value), 64))
        except (TypeError, ValueError):
            radius = "theme"

    return {
        "width": option("width", {"theme", "narrow", "wide", "full"}, "theme"),
        "background": option("background", {"theme", "surface", "primary", "accent", "custom"}, "theme"),
        "background_color": color("background_color", "#FFFFFF"),
        "text": option("text", {"theme", "inverse", "custom"}, "theme"),
        "text_color": color("text_color", "#1C274C"),
        "radius": radius,
        "shadow": option("shadow", {"none", "soft", "lifted"}, "none"),
        "hide_mobile": value.get("hide_mobile") is True,
    }


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
        if item["type"] in _DEFAULT_SECTION_TYPES
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

    normalized_settings = _normalize_custom_embed_settings(settings) if section_type == "custom_embed" else deepcopy(settings)
    if isinstance(settings.get("design"), dict):
        normalized_settings["design"] = _normalize_section_design(settings["design"])

    return {
        "id": raw_id,
        "type": section_type,
        "enabled": raw.get("enabled") is not False,
        "settings": normalized_settings,
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
