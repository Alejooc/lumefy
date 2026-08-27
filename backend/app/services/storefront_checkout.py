"""Safe, tenant-scoped presentation settings for the public checkout."""

from __future__ import annotations

import re
from typing import Any


DEFAULT_CHECKOUT_APPEARANCE: dict[str, Any] = {
    "background_color": "#f4f6fb",
    "card_background_color": "#ffffff",
    "accent_color": "#3c50e0",
    "accent_text_color": "#ffffff",
    "field_background_color": "#f8fafc",
    "border_color": "#d9e1ec",
    "radius": 12,
    "layout": "split",
    "show_logo": True,
    "show_brand_name": True,
}

_HEX_COLOR = re.compile(r"^#[0-9a-fA-F]{6}$")
_CHECKOUT_LAYOUTS = {"split", "stacked"}


def _object(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _safe_hex(value: Any, fallback: str) -> str:
    candidate = str(value or "").strip()
    return candidate if _HEX_COLOR.fullmatch(candidate) else fallback


def _theme_style(theme_settings: Any, key: str, fallback: str) -> str:
    settings = _object(theme_settings)
    global_settings = _object(settings.get("global"))
    styles = {
        **_object(settings.get("styles")),
        **_object(global_settings.get("styles")),
    }
    return _safe_hex(styles.get(key), fallback)


def normalize_checkout_settings(
    settings: Any,
    theme_settings: Any = None,
) -> dict[str, Any]:
    """Return checkout settings with a safe, backwards-compatible appearance block.

    Checkout business rules remain untouched. Only the public presentation block is
    normalized here so arbitrary JSON cannot become CSS or markup in the storefront.
    """
    base = dict(_object(settings))
    appearance = _object(base.get("appearance"))
    default_appearance = {
        **DEFAULT_CHECKOUT_APPEARANCE,
        "background_color": _theme_style(theme_settings, "page_background_color", DEFAULT_CHECKOUT_APPEARANCE["background_color"]),
        "accent_color": _theme_style(theme_settings, "primary_color", DEFAULT_CHECKOUT_APPEARANCE["accent_color"]),
    }

    radius = appearance.get("radius", default_appearance["radius"])
    try:
        radius = max(0, min(24, int(float(radius))))
    except (TypeError, ValueError):
        radius = default_appearance["radius"]

    layout = appearance.get("layout")
    if layout not in _CHECKOUT_LAYOUTS:
        layout = default_appearance["layout"]

    normalized_appearance = {
        "background_color": _safe_hex(appearance.get("background_color"), default_appearance["background_color"]),
        "card_background_color": _safe_hex(appearance.get("card_background_color"), default_appearance["card_background_color"]),
        "accent_color": _safe_hex(appearance.get("accent_color"), default_appearance["accent_color"]),
        "accent_text_color": _safe_hex(appearance.get("accent_text_color"), default_appearance["accent_text_color"]),
        "field_background_color": _safe_hex(appearance.get("field_background_color"), default_appearance["field_background_color"]),
        "border_color": _safe_hex(appearance.get("border_color"), default_appearance["border_color"]),
        "radius": radius,
        "layout": layout,
        "show_logo": appearance.get("show_logo") is not False,
        "show_brand_name": appearance.get("show_brand_name") is not False,
    }
    base["appearance"] = normalized_appearance
    return base
