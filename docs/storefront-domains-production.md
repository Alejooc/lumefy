# Dominios y HTTPS de tiendas

Lumefy utiliza Nginx Proxy Manager (NPM) como entrada pública. El panel se sirve en `ADMIN_DOMAIN`, las tiendas de la plataforma usan `*.PLATFORM_STOREFRONT_DOMAIN` y cada dominio propio obtiene un Proxy Host y certificado independientes.

## Dominios de la plataforma

El Proxy Host wildcard existente apunta al storefront compartido:

```text
*.jaofy.com, jaofy.com -> lumefy-storefront-1:3000
```

Crear una tienda con un subdominio de `jaofy.com` no solicita certificados adicionales.

## Dominio propio de una tienda

1. En **Ecommerce > Configuración > Dominios**, el comercio agrega solo el host que quiere utilizar.
2. Lumefy genera `_lumefy-verification.<dominio>` con un valor TXT único.
3. Al pulsar **Verificar DNS**, el backend valida el TXT y encola el dominio.
4. Antes de crear el host, el worker usa la prueba HTTP de NPM contra su servidor de desafío. Si todavía no existe conectividad DNS, reintenta con espera sin consumir solicitudes de certificados.
5. Cuando la prueba es correcta, crea o completa en NPM un Proxy Host exclusivo hacia `lumefy-storefront-1:3000` y solicita el SSL.
6. NPM emite y renueva el certificado y Lumefy marca el dominio como **Activo**.

El host exacto debe estar registrado en Lumefy. Si se necesitan `example.com` y `www.example.com`, se agregan y verifican como dos dominios.

## Estados

* `PENDING_VERIFICATION`: falta validar el TXT.
* `QUEUED` / `PROVISIONING`: NPM está configurando el host.
* `RETRY`: DNS o NPM aún no están listos; el worker reintentará.
* `ACTIVE`: Proxy Host y certificado están asociados.
* `FAILED`: se agotaron los intentos o existe un conflicto que requiere revisión.

Nunca marques un dominio como verificado o activo directamente en la base de datos.
