# Operación de producción

## Sondas y despliegue

`/healthz` confirma que el proceso está vivo. `/readyz` también comprueba PostgreSQL y es la sonda usada por Docker en producción. No expongas puertos de PostgreSQL, backend, Angular ni Next: Caddy es el único servicio público.

Antes del primer despliegue, copia los dos archivos `.env.production.example`, reemplaza todos los valores de ejemplo y define una contraseña de administrador y `SECRET_KEY` únicos. Mantén `SQL_ECHO=false` en producción para no registrar consultas ni valores operativos.

Comprueba la composición antes de levantarla:

```sh
docker compose --env-file .env.production -f docker-compose.prod.yml config
docker compose --env-file .env.production -f docker-compose.prod.yml up -d --build
docker compose -f docker-compose.prod.yml ps
```

## Respaldo y restauración

El respaldo se genera en formato PostgreSQL personalizado y no se versiona en Git:

```sh
sh scripts/backup-postgres.sh
```

Programa ese comando diariamente y copia los archivos resultantes a almacenamiento externo cifrado. Comprueba una restauración en una base de datos aislada al menos cada mes:

```sh
docker compose -f docker-compose.prod.yml exec -T db createdb -U "$POSTGRES_USER" lumefy_restore_check
docker compose -f docker-compose.prod.yml exec -T db pg_restore -U "$POSTGRES_USER" -d lumefy_restore_check --clean --if-exists < backups/postgres/lumefy-YYYYMMDDTHHMMSSZ.dump
```

No restaures sobre la base de producción sin una ventana de mantenimiento, un respaldo reciente y una verificación previa en un entorno aislado.

## Pagos Wompi

Configura en el dashboard de Wompi la URL de eventos `https://admin.example.com/api/v1/storefront/public/payments/wompi/webhook` (sustituye el dominio). Guarda el secreto de eventos de Wompi como `events_secret` en la configuración privada de la pasarela; no uses la llave de integridad para el webhook. El endpoint valida el checksum SHA-256 de las propiedades dinámicas del evento y puede recibir reintentos sin volver a reservar inventario. Wompi recomienda finalizar la integración con eventos y usar la redirección solo para informar al cliente.
