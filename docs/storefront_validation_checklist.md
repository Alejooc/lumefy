# Storefront Validation Checklist

Checklist operativa para validar lo basico del storefront `storefront_nextmerce` antes de considerarlo listo para uso real.

## 1. Entorno y configuracion

Estado: parcial

- [x] Confirmar `NEXT_PUBLIC_API_URL` en `storefront_nextmerce/.env`
- [ ] Confirmar `NEXT_PUBLIC_SITE_URL` con el dominio real del storefront
- [x] Confirmar `NEXT_PUBLIC_STOREFRONT_ID` o `NEXT_PUBLIC_STOREFRONT_SUBDOMAIN`
- [x] Confirmar `NEXT_IMAGE_ALLOW_LOCAL_IP=true` solo en desarrollo local
- [ ] Confirmar `FRONTEND_URL` del backend apuntando a `storefront_nextmerce`
- [x] Confirmar que backend y frontend resuelven el mismo storefront

Resultado actual:
- `NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1`
- `NEXT_PUBLIC_STOREFRONT_SUBDOMAIN=varyago`
- `NEXT_PUBLIC_SITE_URL` no esta definido en `.env`
- `FRONTEND_URL` no aparecio configurado en `backend/.env`
- Backend publico resuelve el storefront `Varyago`

Criterio de exito:
- El storefront carga sin errores de configuracion
- Las URLs canonicas y de recovery usan el dominio correcto
- Las imagenes cargan sin bloqueos

## 2. Home y navegacion

Estado: parcial

- [x] Validar carga de home con datos reales
- [x] Validar header con logo, telefono y navegacion dinamica
- [x] Validar footer con branding real
- [x] Validar buscador del header
- [ ] Validar links principales del menu
- [ ] Validar `404` para slug inexistente de producto

Resultado actual:
- El storefront publico devuelve branding real de `Varyago`
- Navegacion publica devuelve 1 item de coleccion
- La busqueda en `/products?q=almohada` responde y queda `noindex`
- El slug inexistente ya muestra contenido 404, pero en verificacion local todavia respondio `200` HTTP

Criterio de exito:
- Home renderiza datos del backend
- Header y footer muestran branding correcto
- No hay links rotos

## 3. Catalogo y producto

Estado: parcial

- [x] Validar `/products`
- [ ] Validar filtros por `collection`, `type`, `size`, `color`, `price`, `sort`
- [x] Validar busqueda con `q`
- [x] Validar `/products/[slug]`
- [x] Validar galeria e imagen principal
- [ ] Validar relacionados
- [ ] Validar agregar al carrito desde listado
- [ ] Validar agregar al carrito desde detalle
- [ ] Validar wishlist
- [ ] Validar quick view

Resultado actual:
- La coleccion publica `principal` expone 1 producto: `par-almohada`
- `/products/par-almohada` responde con canonical correcto
- La galeria publica devuelve 2 imagenes

Criterio de exito:
- El catalogo responde a filtros reales
- El detalle de producto carga sin errores
- Cart, wishlist y quick view funcionan con productos reales

## 4. Carrito y checkout

Estado: bloqueado

- [ ] Validar persistencia del carrito
- [ ] Validar actualizacion de cantidades
- [ ] Validar eliminacion de items
- [ ] Validar vaciado de carrito
- [x] Validar preview del checkout
- [ ] Validar creacion de orden
- [ ] Validar `idempotency_key` evitando orden duplicada
- [ ] Validar flujo completo con un `store_payment_gateway` activo
- [ ] Validar pagina `/checkout/success`

Bloqueante:
- Debe existir al menos un `store_payment_gateway` habilitado en la base

Criterio de exito:
- Se puede completar una compra end-to-end
- No se crean ordenes duplicadas por doble submit
- El usuario llega correctamente a success

Resultado actual:
- `checkout/preview` responde correctamente para `par-almohada`
- `checkout/orders` y `payment-intent` fallan con `400`
- Motivo exacto: `Payment provider 'manual_transfer' is not active for this storefront`
- En base hoy hay `0` filas en `store_payment_gateways`

## 5. Auth y cuenta

Estado: parcial

- [x] Validar registro
- [x] Validar login
- [ ] Validar logout
- [x] Validar `/account`
- [x] Validar actualizacion de perfil
- [x] Validar cambio de password
- [x] Validar recovery por email
- [ ] Validar reset password desde link recibido
- [x] Validar listado de ordenes del cliente

Resultado actual:
- Registro, login, `account/me`, `account/profile` y `account/password` responden bien
- Recovery devuelve respuesta neutra correcta
- `account/orders` responde sin error y hoy devuelve `0` ordenes para el usuario validado
- Falta verificar el flujo del link recibido por email

Criterio de exito:
- El usuario puede crear y usar su cuenta
- Recovery llega con el link correcto
- La cuenta muestra ordenes reales del storefront

## 6. Contacto y branding

Estado: parcial

- [x] Validar submit de `/contact`
- [x] Validar branding cargado desde backoffice
- [x] Validar logo
- [x] Validar datos de contacto
- [ ] Validar redes sociales
- [ ] Validar promo banners

Resultado actual:
- `/contact` responde `Your message has been sent successfully`
- Branding publico actual:
- logo configurado
- telefono configurado
- email configurado
- direccion configurada
- redes vacias
- promo banners vacios

Criterio de exito:
- El branding del storefront coincide con lo configurado en backoffice
- El formulario de contacto responde correctamente

## 7. Rutas y compatibilidad

Estado: parcial

- [x] Validar rutas canonicas:
- [x] `/`
- [x] `/products`
- [x] `/products/[slug]`
- [ ] `/login`
- [ ] `/register`
- [ ] `/account`
- [ ] `/password/reset`
- [ ] `/checkout/success`
- [ ] Validar redirects legacy:
- [ ] `/shop-details`
- [ ] `/shop-with-sidebar`
- [ ] `/shop-without-sidebar`
- [ ] `/signin`
- [ ] `/signup`
- [ ] `/my-account`
- [ ] `/reset-password`
- [ ] `/mail-success`

Criterio de exito:
- Las rutas nuevas funcionan como principal
- Las viejas redirigen sin romper enlaces previos

Resultado actual:
- Home, products y product detail quedaron validadas
- Se agregaron redirects a `next.config.js` para varias rutas legacy
- La validacion HTTP final de esos redirects quedo pendiente porque el servidor temporal de Next no quedo estable en la ultima ronda de pruebas

## 8. SEO tecnico basico

Estado: parcial

- [x] Validar `canonical` en home
- [x] Validar `canonical` en `/products`
- [x] Validar `canonical` en `/products/[slug]`
- [x] Validar `noindex` en login, register, account, cart, wishlist, checkout
- [x] Validar `/robots.txt`
- [x] Validar `/sitemap.xml`
- [ ] Validar que `NEXT_PUBLIC_SITE_URL` sea el dominio real

Resultado actual:
- `robots.txt` y `sitemap.xml` responden
- El sitemap incluye `/`, `/products`, `/contact` y `par-almohada`
- Las canonicals hoy salen con `http://localhost:3000` porque falta `NEXT_PUBLIC_SITE_URL`

Criterio de exito:
- Solo se indexan rutas publicas utiles
- El sitemap publica URLs validas del storefront

## 9. Cierre tecnico minimo

Estado: parcial

- [x] Ejecutar `npm run lint` en `storefront_nextmerce`
- [x] Ejecutar `npm run build` en `storefront_nextmerce`
- [x] Ejecutar compilacion del backend
- [x] Confirmar que `storefront_next` sigue intacto

Criterio de exito:
- Front y back compilan
- No se rompio el front anterior

## Orden recomendado de ejecucion

1. Entorno y configuracion
2. Home y navegacion
3. Catalogo y producto
4. Carrito y checkout
5. Auth y cuenta
6. Contacto y branding
7. Rutas y compatibilidad
8. SEO tecnico basico
9. Cierre tecnico minimo

## Bloqueos conocidos hoy

- El flujo real de checkout depende de tener un `store_payment_gateway` activo
- El sitemap usa productos encontrados via colecciones publicas, no un endpoint dedicado de catalogo total
- `size` y `color` siguen dependiendo de la estructura actual de variantes, no de campos estructurados
- `NEXT_PUBLIC_SITE_URL` falta en `storefront_nextmerce/.env`
- `FRONTEND_URL` no quedo visible en `backend/.env`
- No hay `store_payment_gateways` activos para completar checkout real
- El `404` de producto inexistente muestra UI correcta, pero falta confirmar el status HTTP final en una corrida estable de Next
