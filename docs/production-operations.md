# Operación de producción

## Preparación obligatoria

La topología de producción no publica PostgreSQL, Redis, FastAPI, Angular ni Next directamente. El proxy es el único punto de entrada. Antes del primer despliegue:

1. Copia `.env.production.example` a `.env.production` y `backend/.env.production.example` a `backend/.env.production`.
2. Sustituye todos los valores `replace-with-*`. El backend rechaza el arranque en producción si detecta secretos de ejemplo, claves cortas o una clave Fernet inválida.
3. Genera `SECRET_KEY` y `FIRST_SUPERUSER_PASSWORD` independientes. Genera `CREDENTIAL_ENCRYPTION_KEY` con:

   ```sh
   openssl rand 32 | openssl base64 -A | tr '+/' '-_'
   ```

4. Guarda `CREDENTIAL_ENCRYPTION_KEY` también en el gestor externo de secretos o bóveda de recuperación. No la incluyas dentro del respaldo de datos: perderla hace irrecuperables las credenciales cifradas de Wompi y otras pasarelas.
5. Configura el proveedor SMTP y sustituye `MAIL_USERNAME`/`MAIL_PASSWORD`. Producción rechaza credenciales de ejemplo, SMTP autenticado sin TLS y certificados sin validar.
6. Mantén `SQL_ECHO=false` y solo orígenes HTTPS reales en `BACKEND_CORS_ORIGINS`.

Comprueba la configuración antes de arrancar:

```sh
docker compose --env-file .env.production -f docker-compose.prod.yml config --quiet
docker compose --env-file .env.production -f docker-compose.prod.yml up -d --build --wait
sh scripts/smoke-production.sh
```

La migración es un servicio de una sola ejecución. Backend y workers no arrancan hasta que PostgreSQL esté sano y `alembic upgrade head` termine correctamente.

## CI y despliegue

Cada pull request y push a `main` ejecuta:

- instalación Python desde `requirements.lock` con hashes, auditoría, la suite backend y toda la cadena de migraciones en PostgreSQL;
- lint, pruebas y build de Angular, y lint/build de Next;
- auditoría de dependencias runtime de ambos frontends;
- construcción de las tres imágenes y smoke test de la topología de producción.

El entorno `production` de GitHub necesita estos secretos:

- `DEPLOY_HOST`, `DEPLOY_USER`, `DEPLOY_PATH` y `DEPLOY_SSH_KEY`;
- `DEPLOY_KNOWN_HOSTS`: la línea de host SSH verificada por un canal independiente. El workflow no confía automáticamente en el resultado de `ssh-keyscan`.

El despliegue usa exactamente `github.sha`, conserva una etiqueta de imagen por revisión y no se cancela a mitad de ejecución. Cada servicio mantiene la etiqueta exacta de la imagen que ya está ejecutando cuando no recibió cambios; de esta forma, un cambio del storefront no reinicia el backend ni los workers. Cuando ya existen datos, el rollout crea primero un respaldo rápido de PostgreSQL en `backups/pre-deploy/`. En el primer despliegue, cuando no existe ninguno de los volúmenes de datos, omite el respaldo de forma explícita.

Después del smoke test interno, el despliegue recarga Nginx Proxy Manager cuando encuentra su contenedor y comprueba públicamente el panel, el API y los archivos estáticos. Un `502` externo hace fallar el workflow aunque todos los contenedores estén sanos. Define `PROXY_CONTAINER_NAME` en `.env.production` si el contenedor no puede descubrirse automáticamente desde `PROXY_NETWORK`.

## Sondas, logs y alertas

- `/healthz` confirma que el proceso está vivo.
- `/readyz` comprueba también PostgreSQL y es la sonda de readiness.
- Cada respuesta del API incluye `X-Request-ID`. Un identificador válido recibido se conserva; valores inseguros se reemplazan. Los logs de petición contienen el mismo ID, ruta, estado y duración.
- Docker rota cada log a cinco archivos de 10 MB para evitar llenar el disco.

Después de configurar DNS, conecta un monitor externo a `/api/v1/readyz` y una comprobación autenticada de negocio separada. Hasta entonces, ejecuta `sh scripts/smoke-production.sh` y `sh scripts/smoke-public.sh` desde cron o desde el sistema de monitoreo del VPS. Deben alertar como mínimo:

- `/readyz` fallando durante dos comprobaciones seguidas;
- cualquier contenedor requerido detenido o reiniciando;
- disco o volumen de PostgreSQL por encima del 80 %;
- último respaldo verificado con más de 26 horas;
- cola de emails u outbox creciendo sin consumo;
- aumento de pagos pendientes o webhooks rechazados.

## Respaldo completo

El respaldo incluye PostgreSQL, el volumen de archivos subidos, metadatos y checksums SHA-256:

```sh
sh scripts/backup-production.sh
```

Por defecto queda en `backups/production/<fecha-UTC>/` y conserva 14 días. Programa la tarea diariamente:

```cron
0 2 * * * cd /srv/lumefy && sh scripts/backup-production.sh >> /var/log/lumefy-backup.log 2>&1
```

No sustituyas este respaldo completo por los snapshots de `backups/pre-deploy/`: estos últimos contienen únicamente PostgreSQL para que un despliegue no vuelva a comprimir toda la biblioteca de archivos. Se conservan siete días por defecto y su propósito es proteger el cambio de esquema inmediato.

La copia local no es suficiente. Replica cada directorio terminado a almacenamiento externo cifrado e inmutable. Supervisa la antigüedad del último respaldo y prueba una restauración al menos una vez al mes.

## Prueba de restauración

Primero verifica la integridad:

```sh
cd backups/production/20260809T020000Z
sha256sum --check SHA256SUMS
cd ../../..
```

Restaura la base en una base aislada, nunca directamente sobre producción:

```sh
docker compose --env-file .env.production -f docker-compose.prod.yml exec -T db sh -c \
  'createdb -U "$POSTGRES_USER" lumefy_restore_check'
docker compose --env-file .env.production -f docker-compose.prod.yml exec -T db sh -c \
  'pg_restore -U "$POSTGRES_USER" -d lumefy_restore_check --clean --if-exists' \
  < backups/production/20260809T020000Z/database.dump
```

Para probar los archivos en un volumen aislado:

```sh
docker volume create lumefy_restore_static
docker run --rm \
  -v lumefy_restore_static:/target \
  -v "$PWD/backups/production/20260809T020000Z:/backup:ro" \
  alpine:3.22 sh -c 'tar -C /target -xzf /backup/uploads.tar.gz'
```

Verifica conteos, una muestra de pedidos, usuarios, inventario, pasarelas descifrables y archivos servibles. Elimina el entorno aislado solo después de registrar el resultado de la prueba.

## Rollback

`backups/deployments/previous-revision` registra la revisión anterior y cada imagen queda etiquetada con el SHA desplegado. Si falla un despliegue:

1. No borres el respaldo creado antes del rollout.
2. Compara las migraciones entre la revisión actual y la anterior. No ejecutes un downgrade automático si una migración eliminó o transformó datos.
3. Si el esquema sigue siendo compatible, vuelve al código anterior y levántalo con su etiqueta:

   ```sh
   previous=$(cat backups/deployments/previous-revision)
   git diff --quiet && git diff --cached --quiet
   git checkout --detach "$previous"
   LUMEFY_IMAGE_TAG="$previous" \
     docker compose --env-file .env.production -f docker-compose.prod.yml up -d --wait
   sh scripts/smoke-production.sh
   ```

4. Si el esquema no es compatible, activa una ventana de mantenimiento y restaura primero en un entorno aislado. Solo después decide entre migración correctiva o restauración completa.

## Pagos Wompi

Configura en Wompi la URL de eventos `https://admin.example.com/api/v1/storefront/public/payments/wompi/webhook` y sustituye el dominio. Guarda el secreto de eventos como `events_secret`; no uses la llave de integridad para el webhook. El endpoint valida el checksum SHA-256 de las propiedades dinámicas y tolera reintentos sin volver a reservar inventario. La redirección solo informa al cliente: el webhook firmado confirma el pago.
