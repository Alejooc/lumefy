# Storefront Execution Plan

Checklist ejecutable para dejar `storefront_nextmerce` estable antes de activar pagos reales.

## Bloque 1: base y catalogo

- [x] Resolver el tenant por subdominio o dominio configurado.
- [x] Cargar branding, navegacion, colecciones y productos desde backend.
- [x] Aplicar en el storefront `custom_title`, `custom_description`, `price_override` y `compare_at_price`.
- [x] Usar el precio publicado en filtros, ordenamiento, carrito, preview y orden.
- [x] Mantener inventario y disponibilidad como verdad del backend.
- [x] Normalizar imagenes publicas y fallback cuando una imagen no existe.

## Bloque 2: carrito y checkout

- [x] Persistir y actualizar cantidades del carrito sin estado visual desfasado.
- [x] Limitar cantidades al stock disponible y bloquear productos agotados.
- [x] Mostrar feedback al agregar productos y cerrar el drawer al navegar.
- [x] Calcular preview de subtotal, envio, descuentos, impuestos y total en backend.
- [x] Aplicar cupones reales del backend y eliminar el formulario de descuento falso.
- [x] Respetar configuracion de envio, notas, telefono y checkout de invitado/cuenta.
- [x] Validar idempotencia antes de devolver una orden existente.
- [x] Evitar crear ordenes cuando no hay una pasarela habilitada y operativa.
- [x] Reservar inventario al crear la orden y mantener el flujo de estado existente.

## Bloque 3: cuenta y pedidos

- [x] Separar cuentas de clientes del usuario interno del panel administrativo.
- [x] Validar registro, login, sesion, perfil, cambio de password y recovery.
- [x] Aislar tokens y sesiones entre storefronts.
- [x] Rechazar checkout privado sin autenticacion y exigir coincidencia de correo.
- [x] Consultar pedidos reales desde `storefront_orders` con fallback legacy.
- [x] Mostrar direccion, estado, total y detalle de pedido en responsive.
- [x] Enviar confirmacion durable de pedido al correo del cliente cuando exista.
- [x] Eliminar acciones de edicion de pedidos que no tenian endpoint real.

## Bloque 4: UI, UX y responsive

- [x] Mantener la estructura visual del template Mantis/NextMerce sin bloques IA falsos.
- [x] Retirar newsletter, onboarding y enlaces demo que no tienen funcionalidad real.
- [x] Corregir botones, iconos, labels y acciones de carrito/checkout.
- [x] Implementar drawer de filtros movil con backdrop, cierre y bloqueo de scroll.
- [x] Ajustar tabla/modal de pedidos para pantallas pequenas.
- [x] Validar lint y build de produccion del storefront.

## Bloque 5: despliegue y pendientes externos

- [x] Reconstruir backend, workers y storefront en Docker.
- [x] Confirmar `/healthz` de backend y storefront.
- [x] Ejecutar pruebas backend y compilacion Python.
- [x] Ejecutar integracion temporal de catalogo y checkout preview con limpieza de datos.
- [ ] Configurar `NEXT_PUBLIC_SITE_URL`, CORS, `FRONTEND_URL` y dominio real en produccion.
- [ ] Activar y probar una pasarela de pago con credenciales reales/sandbox.
- [ ] Probar retorno post-pago, webhook, conciliacion y correo SMTP en el VPS.
- [ ] Ejecutar smoke test visual con una tienda real en desktop y movil.

## Resultado actual

El storefront queda funcional para catalogo, carrito, checkout manual/configurado, inventario, cuentas y pedidos. El unico bloque que no debe darse por cerrado sin configuracion externa es el de pagos reales, correo SMTP y validacion final sobre el dominio del VPS.
