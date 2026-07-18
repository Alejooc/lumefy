# Operacion SaaS de Lumefy

## Producto

Lumefy opera como un ERP comercial multiempresa. Cada empresa administra catalogo, inventario, compras, ventas, POS, clientes y una o varias tiendas online sin compartir datos con otros tenants.

## Separacion de roles

El superadministrador administra la plataforma: empresas, planes, usuarios globales, configuracion, salud del sistema y catalogo global de apps. No opera una empresa cliente y no debe ver Marketplace, Apps instaladas, Ecommerce ni Facturacion de tenant.

El administrador de empresa opera solo su tenant: Marketplace, apps habilitadas, ecommerce, facturacion, catalogo y modulos operativos. No puede modificar su plan, vencimiento ni estado de suscripcion.

El ecommerce es una app instalable. La empresa debe habilitarla desde `Tienda de Apps` antes de administrarla desde el menu. El plan puede limitar tiendas con la clave `storefronts` en `Plan.limits`; usa `0` para impedir nuevas tiendas o elimina la clave para no establecer limite.

La suscripcion tiene estados `ACTIVE`, `PAST_DUE`, `SUSPENDED` y `CANCELED`. Solo el superadministrador puede cambiar plan, vencimiento o estado. Los administradores de cada empresa solo pueden editar sus datos operativos.

## Dominios de tienda

Cada tienda puede tener un subdominio Lumefy o dominios propios. El storefront consulta la API publica por subdominio, ID o dominio. En produccion, el proxy envia el `Host` original y todas las tiendas se sirven desde el contenedor `storefront`.

Antes de publicar un dominio propio:

1. Crea el dominio en la configuracion de Ecommerce.
2. Apunta el DNS A/AAAA al VPS.
3. Configura TLS con un proxy que gestione certificados, por ejemplo Caddy, Traefik o Certbot.
4. Marca el dominio como verificado solo despues de comprobar DNS y TLS.

## Despliegue

1. Copia `.env.production.example` a `.env.production` y `backend/.env.production.example` a `backend/.env.production`.
2. Sustituye todas las credenciales de ejemplo por secretos aleatorios y define los dominios reales.
3. Ejecuta `docker compose -f docker-compose.prod.yml up -d --build`.
4. Configura los secretos GitHub `DEPLOY_HOST`, `DEPLOY_USER`, `DEPLOY_SSH_KEY` y `DEPLOY_PATH`.
5. Todo push a `main` valida Angular y storefront antes de ejecutar el despliegue remoto.

El compose de produccion ejecuta migraciones antes de arrancar la API. El compose local sigue siendo el entorno de desarrollo.
