# Despliegue con Nginx Proxy Manager

Lumefy no inicia Caddy por defecto en producción. Nginx Proxy Manager (NPM) gestiona TLS y enruta los dominios hacia los contenedores de Lumefy mediante una red Docker externa compartida.

## VPS

1. Identifica la red de NPM con `docker network ls` y define su nombre en `.env.production` como `PROXY_NETWORK`.
2. Crea `.env.production` y `backend/.env.production` desde los archivos `.example`. No subas esos archivos a Git.
3. Ejecuta `docker compose -f docker-compose.prod.yml up -d --build`.

## Proxy hosts en NPM

* Panel admin: `admin.tudominio.com` -> host `frontend`, puerto `80`.
* Storefront comodín: `*.tudominio.com` -> host `storefront`, puerto `3000`. Activa certificado wildcard DNS y HTTP/2.
* Dominios personalizados de tiendas: Lumefy crea un Proxy Host por dominio mediante la API de NPM y lo dirige a `lumefy-storefront-1:3000`.

En el host del panel agrega ubicaciones personalizadas:

* `/api` -> `backend:8000`
* `/static` -> `backend:8000`

Activa WebSockets en todos los proxy hosts. Los nombres `frontend`, `storefront` y `backend` se resuelven porque NPM y Lumefy comparten `PROXY_NETWORK`.

## Aprovisionamiento automático de dominios personalizados

1. Crea en NPM un usuario técnico con correo válido y permisos para administrar Proxy Hosts y certificados. El correo es necesario para las solicitudes de Let's Encrypt. No reutilices la cuenta personal del administrador.
2. Verifica el nombre del contenedor de NPM dentro de `PROXY_NETWORK` y configura `backend/.env.production`:

   ```text
   NPM_PROVISIONING_ENABLED=true
   NPM_API_URL=http://nginx-proxy-manager:81/api
   NPM_IDENTITY=automation@example.com
   NPM_PASSWORD=UNA_CLAVE_LARGA_Y_ALEATORIA
   NPM_FORWARD_SCHEME=http
   NPM_STOREFRONT_HOST=lumefy-storefront-1
   NPM_STOREFRONT_PORT=3000
   NPM_VERIFY_SSL=true
   NPM_PROVISIONING_MAX_ATTEMPTS=3
   NPM_PROVISIONING_CONCURRENCY=1
   ```

3. Despliega también `domain-provisioning-worker`. El servicio viene incluido en `docker-compose.prod.yml`.
4. El comercio agrega el dominio en Lumefy, publica el TXT y pulsa **Verificar DNS**. Solo después de validar propiedad, Lumefy coloca el dominio en la cola.
5. El worker comprueba primero que el dominio llega por HTTP al servidor de desafío de NPM; después crea o completa un Proxy Host HTTP exclusivo y solicita el certificado de Let's Encrypt.

Cada dominio se procesa de forma idempotente. Lumefy conserva los identificadores del Proxy Host y del certificado, limita los reintentos y muestra el último error en Ecommerce > Configuración > Dominios.

Mantén `NPM_PROVISIONING_CONCURRENCY=1`: NPM ejecuta una sola instancia de Certbot y las emisiones simultáneas pueden rechazarse. Las altas concurrentes permanecen en cola y se atienden secuencialmente.

Si el dominio utiliza el proxy naranja de Cloudflare y la prueba HTTP no alcanza NPM, el comercio debe dejar temporalmente el registro como **Solo DNS** hasta que el estado sea **Activo**. Después puede volver a habilitar el proxy.
