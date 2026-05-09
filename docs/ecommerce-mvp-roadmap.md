# Ecommerce MVP Roadmap

## Objetivo

Agregar ecommerce multi-tenant al SaaS sin crear una instancia separada por empresa. Cada empresa tendra una tienda propia dentro del mismo motor compartido.

## Principios

- Un solo motor ecommerce para todas las empresas.
- Cada empresa decide que productos publica.
- Las colecciones son agrupaciones comerciales, separadas de categorias.
- Un producto puede pertenecer a muchas colecciones.
- El menu de la tienda puede apuntar a colecciones, categorias, paginas o URLs.
- Cada empresa configura y activa sus propias pasarelas de pago.

## Primer sprint backend

Este sprint deja solo la base administrativa del ecommerce:

- `storefronts`
- `storefront_domains`
- `store_collections`
- `published_products`
- `store_collection_products`
- `store_navigation_items`
- `store_payment_gateways`

## Lo que ya queda soportado en el modelo

### Tienda por empresa

- nombre, slug y subdominio
- tema seleccionado
- configuracion de tema
- configuracion basica de checkout y SEO

### Productos publicados

- un producto interno no se publica automaticamente
- la empresa elige que producto sale al ecommerce
- el producto publicado puede tener slug, precio y contenido SEO propios

### Colecciones

- una coleccion agrupa productos con objetivo comercial
- ejemplo: `cubrelechos`, `ofertas`, `nuevos-ingresos`
- un mismo producto puede estar en varias colecciones

### Menu

Cada item de navegacion puede apuntar a:

- `collection`
- `category`
- `page`
- `url`

### Pasarelas por empresa

Cada empresa puede:

- configurar credenciales por proveedor
- activar o desactivar proveedores
- usar modo sandbox o produccion
- guardar datos como `api key`, `secret`, `merchant_id` y configuracion adicional

Ejemplos previstos:

- `paypal`
- `wompi`
- `payu`
- `addi`

## Lo que no entra en este sprint

- storefront publico
- checkout real
- integraciones activas con pasarelas
- pedidos web
- CMS visual
- dominios custom verificados automaticamente

## Siguiente orden recomendado

1. Crear migracion y aplicar tablas ecommerce.
2. Construir pantallas admin para tienda, colecciones, menu y pasarelas.
3. Crear API publica del storefront.
4. Construir frontend storefront separado.
5. Implementar checkout y orden web.
