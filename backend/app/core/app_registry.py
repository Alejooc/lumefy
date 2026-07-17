from typing import Any, Dict, List


APP_REGISTRY: List[Dict[str, Any]] = [
    {
        "slug": "ecommerce",
        "name": "Ecommerce",
        "description": "Tienda online nativa conectada con catalogo, inventario, pedidos y clientes.",
        "category": "Canales de venta",
        "version": "1.0.0",
        "icon": "shop",
        "requested_scopes": ["products:read", "inventory:read", "sales:create", "clients:write"],
        "capabilities": ["storefront", "checkout", "custom_domains", "catalog_sync"],
        "pricing_model": "included",
        "monthly_price": 0,
        "config_schema": {
            "type": "object",
            "properties": {
                "allow_custom_domains": {"type": "boolean", "title": "Permitir dominios propios"},
                "default_currency": {"type": "string", "title": "Moneda por defecto"},
            },
        },
        "default_config": {
            "allow_custom_domains": True,
            "default_currency": "USD",
        },
        "setup_url": "/apps/ecommerce",
    },
    {
        "slug": "pos_module",
        "name": "Punto de Venta (POS)",
        "description": "Sistema de cobro rapido para mostrador, optimizado para flujo de caja y ticket.",
        "category": "Ventas",
        "version": "1.0.0",
        "icon": "calculator",
        "requested_scopes": ["sales:create", "inventory:write", "products:read"],
        "capabilities": ["pos_screen", "receipt_printing", "inventory_sync"],
        "pricing_model": "included",
        "monthly_price": 0,
        "config_schema": {
            "type": "object",
            "properties": {
                "thermal_printer_paper": {
                    "type": "string",
                    "title": "Tamano de Papel",
                    "enum": ["80mm", "58mm"],
                },
                "allow_negative_stock": {"type": "boolean", "title": "Permitir ventas sin stock"},
                "default_cash_drawer": {"type": "string", "title": "Caja Registradora Predeterminada"},
                "require_manager_for_void": {"type": "boolean", "title": "Requerir clave para anular ventas"},
                "show_sessions_manager": {"type": "boolean", "title": "Mostrar gestor de cajas"},
                "session_visibility_scope": {
                    "type": "string",
                    "title": "Visibilidad de cajas",
                    "enum": ["own", "branch", "company"],
                },
                "allow_multiple_open_sessions_per_branch": {
                    "type": "boolean",
                    "title": "Permitir varias cajas abiertas por sucursal (usuarios distintos)",
                },
                "allow_enter_other_user_session": {
                    "type": "boolean",
                    "title": "Permitir entrar a caja de otro usuario",
                },
            },
        },
        "default_config": {
            "thermal_printer_paper": "80mm",
            "allow_negative_stock": False,
            "default_cash_drawer": "Main Register",
            "require_manager_for_void": True,
            "show_sessions_manager": True,
            "session_visibility_scope": "branch",
            "allow_multiple_open_sessions_per_branch": True,
            "allow_enter_other_user_session": False,
        },
        "setup_url": "/apps/installed/pos_module",
    },
]
