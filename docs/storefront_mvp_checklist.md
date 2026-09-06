# Storefront MVP Checklist

## Cerrado

- Home funcional con branding y bloques administrables.
- Catalogo `/products` con busqueda, filtros y paginacion real.
- Detalle de producto funcional.
- Carrito funcional.
- Checkout funcional con pasarelas dinamicas desde backend.
- Auth storefront: registro, login, cuenta y reset password.
- SEO basico: canonical, robots y sitemap.
- Menu storefront administrable desde backoffice.
- Backoffice de pagos listo para configurar proveedores por tienda.
- Wompi preparado con Web Checkout generado automaticamente desde backend.
- Reserva y liberacion de inventario con idempotencia y callbacks de pago.
- Caducidad de pedidos pendientes por medio de pago, con conciliacion segura.
- Seguimiento de devoluciones y reembolso manual trazable.
- Promociones porcentuales por colección o producto publicadas, con vigencia, prioridad y aplicación server-side sobre la lista de precios.

## Pendiente para MVP real

1. **Validar** compra end-to-end con una pasarela activa real.
2. **Validar** retorno post-pago, callbacks repetidos y conciliacion del pedido.
3. **Validar** concurrencia de ultima unidad e idempotencia con PostgreSQL.
4. **Validar** checkout completo en movil.
5. Validar menu, branding y home con data final del cliente.
6. Revisar errores y mensajes de pago en entorno real.
7. Definir flujo final de Addi segun documentacion/credenciales oficiales del aliado.
8. Validar promociones con una tienda real: colección, producto puntual, vigencia, solapamiento e impacto en checkout.

## Notas de pagos

- Wompi usa documentacion oficial de Web Checkout y firma de integridad.
- Addi queda preparado por configuracion de `checkout_url`, pero no se implemento una integracion propietaria sin documentacion tecnica oficial publica verificable.
- El checkout ya no depende de un listado hardcodeado de metodos; consume pasarelas habilitadas desde backend.
