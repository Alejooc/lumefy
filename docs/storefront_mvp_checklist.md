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

## Pendiente para MVP real

1. Probar compra end-to-end con una pasarela activa real.
2. Validar retorno post-pago y conciliacion basica del estado del pedido.
3. Endurecer stock al confirmar checkout.
4. Probar checkout completo en movil.
5. Validar menu, branding y home con data final del cliente.
6. Revisar errores y mensajes de pago en entorno real.
7. Definir flujo final de Addi segun documentacion/credenciales oficiales del aliado.

## Notas de pagos

- Wompi usa documentacion oficial de Web Checkout y firma de integridad.
- Addi queda preparado por configuracion de `checkout_url`, pero no se implemento una integracion propietaria sin documentacion tecnica oficial publica verificable.
- El checkout ya no depende de un listado hardcodeado de metodos; consume pasarelas habilitadas desde backend.
