# Storefront Execution Plan

## Estado actual

- [x] Modelar órdenes ecommerce y cliente storefront de forma explícita en backend, reemplazando la dependencia en `sales.notes`
- [x] Conectar `account/orders` y `checkout` al nuevo modelo de órdenes ecommerce
- [ ] Exponer atributos/variantes públicas y habilitar filtros reales de `size` y `color` si existen datos consistentes
- [ ] Completar branding administrable del storefront desde backoffice y reflejarlo en NextMerce
- [ ] Decidir y limpiar páginas demo del template que no se usarán o conectarlas a backend
- [ ] Endurecer checkout: validaciones, idempotencia, errores de pago y consistencia de stock

## Notas

- Las órdenes nuevas del storefront ahora se guardan en `storefront_orders` y se relacionan explícitamente con `sales`.
- `account/orders` ya consulta primero `storefront_orders` y mantiene fallback para órdenes legacy encontradas en `sales.notes`.
- El checkout enlaza `sales.client_id` cuando puede resolver o crear un `Client` por email.
