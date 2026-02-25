from typing import Any, Dict, List


APP_REGISTRY: List[Dict[str, Any]] = [
    {
        "slug": "demo-hello",
        "name": "Demo Hello App",
        "description": "App base de ejemplo para aprender como crear nuevas integraciones.",
        "category": "Productividad",
        "version": "1.0.0",
        "icon": "rocket",
        "requested_scopes": ["apps:read", "apps:write"],
        "capabilities": ["embedded_page", "settings_form"],
        "pricing_model": "free",
        "monthly_price": 0,
        "config_schema": {
            "welcome_message": "string",
            "accent_color": "string",
        },
        "default_config": {
            "welcome_message": "Hola desde tu primera app de Lumefy",
            "accent_color": "#4680ff",
        },
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
