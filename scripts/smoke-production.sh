#!/usr/bin/env sh
set -eu

COMPOSE_FILE=${COMPOSE_FILE:-docker-compose.prod.yml}
ROOT_ENV_FILE=${ROOT_ENV_FILE:-.env.production}
BACKEND_ENV_FILE=${BACKEND_ENV_FILE:-./backend/.env.production}

export ROOT_ENV_FILE BACKEND_ENV_FILE
compose() {
  docker compose --env-file "$ROOT_ENV_FILE" -f "$COMPOSE_FILE" "$@"
}

for service in db redis backend outbox-relay operations-consumer email-delivery-worker integration-sync-worker frontend storefront; do
  if ! compose ps --status running --services | grep -qx "$service"; then
    echo "Required service is not running: $service" >&2
    compose ps
    exit 1
  fi
done

compose exec -T backend python -c \
  "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/healthz', timeout=5).read(); urllib.request.urlopen('http://127.0.0.1:8000/readyz', timeout=5).read()"
compose exec -T storefront node -e \
  "fetch('http://127.0.0.1:3000/healthz').then(r => { if (!r.ok) throw new Error(String(r.status)); }).catch(e => { console.error(e); process.exit(1); })"
compose exec -T frontend wget -q -O /dev/null http://127.0.0.1/

echo "Internal production smoke checks passed."
