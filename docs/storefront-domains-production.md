# Dominios y HTTPS de tiendas

La aplicación sirve el panel administrativo en `ADMIN_DOMAIN` y cada tienda en
un subdominio de `PLATFORM_STOREFRONT_DOMAIN`. Caddy gestiona HTTPS y almacena
los certificados en el volumen `caddy_data`.

## Preparar la plataforma

1. Configure `ADMIN_DOMAIN`, `PLATFORM_STOREFRONT_DOMAIN` y `ACME_EMAIL` en el
   archivo de entorno de producción.
2. Cree un registro `A` para el dominio del panel y un `A` wildcard para las
   tiendas. Ejemplo para `lumefy.shop`:

   ```text
   admin.lumefy.shop   A   IP_DEL_SERVIDOR
   *.lumefy.shop       A   IP_DEL_SERVIDOR
   ```

3. Abra los puertos TCP 80 y 443 hacia el servidor y despliegue con
   `docker compose -f docker-compose.prod.yml up -d`.
4. Compruebe `https://admin.lumefy.shop` y una tienda existente, por ejemplo
   `https://varyago.lumefy.shop`. El primer acceso puede tardar unos segundos
   mientras Caddy obtiene el certificado.

## Dominio propio de una tienda

1. En **Ecommerce > Configuración > Dominios**, agregue solo el host, por
   ejemplo `tienda.cliente.com`.
2. Copie el registro TXT que muestra Lumefy:

   ```text
   _lumefy-verification.tienda.cliente.com  TXT  lumefy-verification=TOKEN
   ```

3. Cuando el TXT haya propagado, pulse **Verificar DNS**. Hasta ese momento el
   dominio no resuelve hacia ninguna tienda y Caddy no puede solicitar un
   certificado para él.
4. Después de verificarlo, apunte el host al servidor mediante `A` o `CNAME`.
   Visite el dominio por HTTPS; Caddy emitirá y renovará el certificado.

No marque ni edite la verificación manualmente: el backend solo la concede al
encontrar el token TXT exacto.
