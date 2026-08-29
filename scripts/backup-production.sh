#!/usr/bin/env sh
set -eu

# Run from the repository root. The resulting directory contains the database,
# uploaded media, metadata and checksums needed for a complete restore.
umask 077

COMPOSE_FILE=${COMPOSE_FILE:-docker-compose.prod.yml}
ROOT_ENV_FILE=${ROOT_ENV_FILE:-.env.production}
BACKEND_ENV_FILE=${BACKEND_ENV_FILE:-./backend/.env.production}
BACKUP_HELPER_IMAGE=${BACKUP_HELPER_IMAGE:-alpine:3.22@sha256:14358309a308569c32bdc37e2e0e9694be33a9d99e68afb0f5ff33cc1f695dce}
BACKUP_MODE=${BACKUP_MODE:-full}

test -s "$ROOT_ENV_FILE"
test -s "$BACKEND_ENV_FILE"

read_root_env() {
  key=$1
  sed -n "s/^${key}=//p" "$ROOT_ENV_FILE" | tail -n 1 | tr -d '\r'
}

configured_backup_dir=$(read_root_env BACKUP_DIR)
configured_retention_days=$(read_root_env BACKUP_RETENTION_DAYS)
configured_static_volume=$(read_root_env BACKEND_STATIC_VOLUME)

BACKUP_DIR=${BACKUP_DIR:-${configured_backup_dir:-./backups/production}}
RETENTION_DAYS=${BACKUP_RETENTION_DAYS:-${configured_retention_days:-14}}
STATIC_VOLUME=${BACKEND_STATIC_VOLUME:-${configured_static_volume:-lumefy_backend_static}}

case "$BACKUP_MODE" in
  full|database) ;;
  *)
    echo "BACKUP_MODE must be either 'full' or 'database'." >&2
    exit 1
    ;;
esac

if [ "$BACKUP_MODE" = "full" ]; then
  case "$STATIC_VOLUME" in
    ""|[-._]*|*[!a-zA-Z0-9_.-]*)
      echo "Refusing an invalid Docker volume name: $STATIC_VOLUME" >&2
      exit 1
      ;;
  esac
fi

case "$BACKUP_DIR" in
  ""|"/"|"."|"..")
    echo "Refusing an unsafe backup directory: $BACKUP_DIR" >&2
    exit 1
    ;;
esac

case "$RETENTION_DAYS" in
  *[!0-9]*|"")
    echo "BACKUP_RETENTION_DAYS must be a non-negative integer." >&2
    exit 1
    ;;
esac

export ROOT_ENV_FILE BACKEND_ENV_FILE
compose() {
  docker compose --env-file "$ROOT_ENV_FILE" -f "$COMPOSE_FILE" "$@"
}

mkdir -p "$BACKUP_DIR"
timestamp=$(date -u +%Y%m%dT%H%M%SZ)
temporary="$BACKUP_DIR/.pending-$timestamp-$$"
target="$BACKUP_DIR/$timestamp"

case "$temporary" in
  "$BACKUP_DIR"/.pending-*) ;;
  *)
    echo "Refusing an unsafe temporary directory: $temporary" >&2
    exit 1
    ;;
esac

cleanup() {
  rm -rf -- "$temporary"
}
trap cleanup EXIT HUP INT TERM

mkdir "$temporary"

compose exec -T db sh -c \
  'PGPASSWORD="$POSTGRES_PASSWORD" pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc' \
  > "$temporary/database.dump"
test -s "$temporary/database.dump"
compose exec -T db pg_restore --list < "$temporary/database.dump" > /dev/null

if [ "$BACKUP_MODE" = "full" ]; then
  absolute_temporary=$(cd "$temporary" && pwd)
  # Git Bash needs a native Windows bind source when argument conversion is disabled.
  if command -v cygpath >/dev/null 2>&1; then
    absolute_temporary=$(cygpath -w "$absolute_temporary")
  fi
  # The shared volume contains files created by the non-root API user and
  # legacy uploads may have stricter ownership or mode bits. The backup
  # helper is read-only and only receives the static volume, so it must read
  # as root to produce a complete archive instead of silently losing media.
  docker run --rm --read-only \
    --user 0:0 \
    --volume "$STATIC_VOLUME:/source:ro" \
    --volume "$absolute_temporary:/backup" \
    "$BACKUP_HELPER_IMAGE" \
    tar -C /source -czf /backup/uploads.tar.gz .
  test -s "$temporary/uploads.tar.gz"
  docker run --rm --read-only \
    --user "$(id -u):$(id -g)" \
    --volume "$absolute_temporary:/backup:ro" \
    "$BACKUP_HELPER_IMAGE" \
    tar -tzf /backup/uploads.tar.gz > /dev/null
fi

revision=$(git rev-parse HEAD 2>/dev/null || printf 'unknown')
cat > "$temporary/metadata.txt" <<EOF
created_at_utc=$timestamp
git_revision=$revision
compose_file=$COMPOSE_FILE
backup_mode=$BACKUP_MODE
static_volume=$STATIC_VOLUME
EOF

(
  cd "$temporary"
  if [ "$BACKUP_MODE" = "full" ]; then
    sha256sum database.dump uploads.tar.gz metadata.txt > SHA256SUMS
  else
    sha256sum database.dump metadata.txt > SHA256SUMS
  fi
  sha256sum --check SHA256SUMS
)

mv "$temporary" "$target"
trap - EXIT HUP INT TERM

find "$BACKUP_DIR" \
  -mindepth 1 -maxdepth 1 -type d -name '20??????T??????Z' \
  -mtime "+$RETENTION_DAYS" -exec rm -rf -- {} +

echo "Production $BACKUP_MODE backup created and verified: $target"
