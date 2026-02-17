# App Store Interno - Guia Rapida

## Flujo base por app
1. Registrar app en `DEFAULT_APPS` de `backend/app/api/v1/endpoints/apps.py`.
2. Ejecutar migraciones si agregas nuevas tablas/campos.
3. Instalar app por empresa desde `/apps`.
4. Guardar configuracion JSON desde la UI.
5. Exponer endpoint funcional en backend (ejemplo: `/apps/demo/hello`).
6. Consumir endpoint desde frontend donde lo necesites.

## Contrato recomendado para nuevas apps
- `slug`: identificador unico (`wompi-payments`, `google-sheets-sync`).
- `config_schema`: llaves esperadas (ejemplo: `api_key`, `webhook_secret`).
- `default_config`: valores por defecto.
- Endpoint de accion de app: `/api/v1/apps/<slug>/...`

## Permisos
- Gestion de apps por empresa: `manage_company`.
- Uso funcional de app: segun modulo (ventas, reportes, etc.) o autenticado base.

## Ejemplo minimo para clonar
Usa `demo-hello` como plantilla:
- Catalogo/instalacion/config ya resuelto.
- Endpoint de prueba listo: `GET /api/v1/apps/demo/hello`.
