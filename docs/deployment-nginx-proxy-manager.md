# Despliegue con Nginx Proxy Manager

Lumefy no inicia Caddy por defecto en producción. Nginx Proxy Manager (NPM) gestiona TLS y enruta los dominios hacia los contenedores de Lumefy mediante una red Docker externa compartida.

## VPS

1. Identifica la red de NPM con `docker network ls` y define su nombre en `.env.production` como `PROXY_NETWORK`.
2. Crea `.env.production` y `backend/.env.production` desde los archivos `.example`. No subas esos archivos a Git.
3. Ejecuta `docker compose -f docker-compose.prod.yml up -d --build`.

## Proxy hosts en NPM

* Panel admin: `admin.tudominio.com` -> host `frontend`, puerto `80`.
* Storefront comodín: `*.tudominio.com` -> host `storefront`, puerto `3000`. Activa certificado wildcard DNS y HTTP/2.
* Dominios personalizados de tiendas: crea un Proxy Host por dominio hacia `storefront:3000`, o usa un wildcard compatible con tu proveedor DNS.

En el host del panel agrega ubicaciones personalizadas:

* `/api` -> `backend:8000`
* `/static` -> `backend:8000`

Activa WebSockets en todos los proxy hosts. Los nombres `frontend`, `storefront` y `backend` se resuelven porque NPM y Lumefy comparten `PROXY_NETWORK`.
