# Matriz De Permisos MVP (Congelada)

Fecha de corte: 2026-02-26

Esta matriz queda congelada para salida MVP. Los roles base no deben editarse ni eliminarse desde UI/API:

- `GERENCIA`
- `SUPERVISOR`
- `CAJA`
- `ADMINISTRADOR`
- `LOGISTICA`
- `INVENTARIO_COMPRAS`
- `REPORTES`

## Reglas operativas

- `CAJA`: operacion POS diaria, sin capacidad de reapertura de cajas ni anulaciones gerenciales.
- `SUPERVISOR`: control operativo de ventas y caja, incluyendo reapertura de caja.
- `GERENCIA`: control integral (empresa, usuarios, inventario, ventas, reportes, POS).

## Permisos por rol (resumen)

### `CAJA`

- `view_dashboard`
- `view_products`
- `manage_clients`
- `create_sales`
- `view_sales`
- `pos_access`

### `SUPERVISOR`

- `view_dashboard`
- `view_products`
- `manage_clients`
- `create_sales`
- `view_sales`
- `manage_sales`
- `pos_access`
- `view_reports`

### `GERENCIA`

- `view_dashboard`
- `manage_company`
- `manage_settings`
- `manage_users`
- `view_products`
- `manage_inventory`
- `view_inventory`
- `manage_clients`
- `create_sales`
- `view_sales`
- `manage_sales`
- `view_reports`
- `pos_access`

## Politica de cambios

- Cualquier cambio de esta matriz se hace por versionado de codigo y aprobacion explicita.
- No se permiten cambios manuales en roles base MVP en produccion.
