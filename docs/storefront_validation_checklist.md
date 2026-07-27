# Storefront Validation Checklist

Checklist de validacion para `storefront_nextmerce` antes de considerarlo listo para produccion.

## Configuracion

- [x] Backend, storefront y workers levantan con Docker.
- [x] Backend responde `GET /healthz` y `GET /readyz`.
- [x] Storefront responde `GET /healthz`.
- [ ] Definir `NEXT_PUBLIC_SITE_URL` con el dominio publico real.
- [ ] Definir `FRONTEND_URL`, CORS y dominio de storefront en produccion.
- [ ] Confirmar que las URLs de imagenes y API usan HTTPS en el VPS.

## Catalogo

- [x] Home, header, footer y navegacion usan datos del tenant.
- [x] Catalogo, busqueda, filtros, ordenamiento y paginacion usan backend.
- [x] El storefront respeta titulo, descripcion y precios publicados por tienda.
- [x] Detalle, galeria, stock y productos relacionados no dependen de datos ficticios.
- [ ] Ejecutar smoke test con productos reales del tenant final.

## Carrito y checkout

- [x] Agregar, quitar, vaciar y actualizar cantidades.
- [x] Limitar cantidades al stock y mostrar agotados correctamente.
- [x] Feedback visual al agregar y cierre del drawer al navegar.
- [x] Preview server-side de subtotal, envio, descuento, impuestos y total.
- [x] Cupones y configuracion de checkout del storefront.
- [x] Idempotencia y validacion de inventario server-side.
- [x] Checkout de invitado y checkout restringido a cuenta.
- [ ] Activar una pasarela y ejecutar compra end-to-end en sandbox.
- [ ] Verificar retorno, webhook, conciliacion y correo de pago.

## Cuenta y pedidos

- [x] Registro, login, logout, perfil y cambio de password.
- [x] Recovery y reset usan la tienda correcta.
- [x] Sesiones aisladas entre tenants.
- [x] `/account` muestra pedidos reales y direccion de envio.
- [x] Confirmacion durable de pedido por correo cuando SMTP esta configurado.
- [ ] Probar reset desde un correo real en el VPS.

## Responsive y accesibilidad

- [x] Drawer de filtros movil con backdrop, cierre y bloqueo de scroll.
- [x] Carrito movil con acciones visibles y navegacion consistente.
- [x] Checkout movil sin formularios anidados ni botones recortados.
- [x] Modal y tabla de pedidos adaptados a pantallas pequenas.
- [x] Iconos principales implementados con SVG inline o iconos existentes del template.
- [ ] Revisar visualmente desktop y movil sobre el dominio final.

## Calidad tecnica

- [x] `npm run lint` sin errores.
- [x] `npm run build` exitoso.
- [x] Pruebas backend exitosas.
- [x] `python -m compileall -q app` exitoso.
- [x] Integracion temporal de catalogo y checkout preview exitosa con limpieza.
- [ ] Ejecutar smoke test final despues del deploy.

## Criterio de cierre

El storefront puede considerarse operativo cuando las tareas externas pendientes esten verificadas: variables HTTPS del VPS, una pasarela configurada, retorno/webhook, SMTP y smoke test visual con datos reales.
