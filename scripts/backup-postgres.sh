#!/usr/bin/env sh
set -eu

# Run from the repository root, for example from cron:
# 0 2 * * * cd /srv/lumefy && sh scripts/backup-postgres.sh
COMPOSE_FILE=${COMPOSE_FILE:-docker-compose.prod.yml}
BACKUP_DIR=${BACKUP_DIR:-./backups/postgres}
RETENTION_DAYS=${BACKUP_RETENTION_DAYS:-14}

case "$BACKUP_DIR" in
  ""|"/")
    echo "Refusing an unsafe backup directory." >&2
    exit 1
    ;;
esac

mkdir -p "$BACKUP_DIR"
timestamp=$(date -u +%Y%m%dT%H%M%SZ)
target="$BACKUP_DIR/lumefy-$timestamp.dump"

docker compose -f "$COMPOSE_FILE" exec -T db sh -c \
  'PGPASSWORD="$POSTGRES_PASSWORD" pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc' > "$target"

test -s "$target"
find "$BACKUP_DIR" -type f -name 'lumefy-*.dump' -mtime +"$RETENTION_DAYS" -delete
echo "Backup created: $target"
