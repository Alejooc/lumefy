# App Marketplace - Enfoque Shopify (Base)

## Objetivo
Pasar de "activar/desactivar modulos" a un marketplace con:
- permisos explicitos por app (`requested_scopes` y `granted_scopes`),
- capacidades declarativas (`capabilities`),
- lifecycle auditable (`install`, `uninstall`, `config_update`),
- metadata de producto (`pricing_model`, `monthly_price`, `docs_url`, `support_url`).

## Flujo recomendado por app
1. Registrar la app en `APP_REGISTRY`:
   - `backend/app/core/app_registry.py`
2. Ejecutar migraciones Alembic.
3. Publicar/editar app desde `/apps/admin` (super admin).
4. Instalar por empresa desde `/apps/store`:
   - se muestran scopes solicitados,
   - se instala con `granted_scopes` y `target_version`.
5. Configurar app en `/apps/installed/:slug`.
6. Revisar eventos en `GET /api/v1/apps/installed/{slug}/events`.

## Contrato de app (backend)
- `slug`: identificador unico.
- `requested_scopes`: permisos solicitados por la app.
- `capabilities`: capacidades funcionales (ej. `pos_screen`, `webhook_consumer`).
- `config_schema` / `default_config`: configuracion renderizable.
- `pricing_model`: `free`, `included`, `paid`.
- `monthly_price`: costo mensual cuando aplique.
- `setup_url`, `docs_url`, `support_url`: UX operativa.

## Endpoints clave
- `GET /apps/catalog`
- `GET /apps/installed`
- `GET /apps/installed/{slug}`
- `GET /apps/installed/{slug}/events`
- `POST /apps/install/{slug}` body: `{ granted_scopes: string[], target_version?: string }`
- `POST /apps/uninstall/{slug}`
- `PUT /apps/config/{slug}`

## Seguridad y operaciones (fase 2)
- API key por instalacion:
  - se genera en `install`,
  - rota con `POST /apps/installed/{slug}/rotate-api-key`,
  - solo se devuelve en claro al crear/rotar.
- Webhooks firmados HMAC SHA256:
  - secret por instalacion (`rotate-webhook-secret`),
  - test manual `POST /apps/installed/{slug}/webhooks/test`,
  - headers: `X-Lumefy-Event`, `X-Lumefy-Signature`.
- Billing resumen por app:
  - `GET /apps/installed/{slug}/billing`.

## Seguridad y operaciones (fase 3)
- Client credentials por instalacion:
  - `oauth_client_id` + `client_secret` rotatorio,
  - endpoint: `POST /apps/installed/{slug}/rotate-client-secret`.
- Auditoria de entregas webhook:
  - `GET /apps/installed/{slug}/webhooks/deliveries`.
- Reintento manual de entrega fallida:
  - `POST /apps/installed/{slug}/webhooks/deliveries/{delivery_id}/retry`.

## Regla de visibilidad por capacidad
- UI y endpoints sensibles ahora dependen de `capabilities` de cada app.
- `webhook_consumer`:
  - habilita test webhook, rotate secret, deliveries y retry.
- `external_api`:
  - habilita `oauth_client_id/client_secret` y su rotacion.
- Apps internas como `pos_module` (sin esas capacidades) no muestran ese bloque operativo.

## Reglas UI/Navegacion
- El menu debe decidir visibilidad por `AppRegistry` + apps instaladas activas.
- Ejemplo actual: POS (`pos_module`) habilita nav item `pos`.

## Nota de compatibilidad
La migracion agrega campos nuevos a `app_definitions` y `company_app_installs`, y crea `app_install_events`.
