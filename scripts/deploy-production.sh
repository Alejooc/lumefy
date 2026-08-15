#!/usr/bin/env sh
set -eu

# The caller must first check out the exact reviewed commit. In CI this script
# receives GITHUB_SHA as LUMEFY_IMAGE_TAG, keeping each release image addressable.
COMPOSE_FILE=${COMPOSE_FILE:-docker-compose.prod.yml}
ROOT_ENV_FILE=${ROOT_ENV_FILE:-.env.production}
BACKEND_ENV_FILE=${BACKEND_ENV_FILE:-./backend/.env.production}
LUMEFY_IMAGE_TAG=${LUMEFY_IMAGE_TAG:-$(git rev-parse --short=12 HEAD)}
PREVIOUS_REVISION=${PREVIOUS_REVISION:-unknown}

export COMPOSE_FILE ROOT_ENV_FILE BACKEND_ENV_FILE LUMEFY_IMAGE_TAG

test -s "$ROOT_ENV_FILE"
test -s "$BACKEND_ENV_FILE"

compose() {
  docker compose --env-file "$ROOT_ENV_FILE" -f "$COMPOSE_FILE" "$@"
}

show_deploy_diagnostics() {
  echo "Production stack failed to become healthy. Current state:" >&2
  compose ps -a >&2 || true
  echo "Migration service logs:" >&2
  compose logs --no-color --tail=200 migrate >&2 || true
}

read_root_env() {
  key=$1
  sed -n "s/^${key}=//p" "$ROOT_ENV_FILE" | tail -n 1 | tr -d '\r'
}

configured_postgres_volume=$(read_root_env POSTGRES_VOLUME_NAME)
configured_static_volume=$(read_root_env BACKEND_STATIC_VOLUME)
POSTGRES_VOLUME_NAME=${POSTGRES_VOLUME_NAME:-${configured_postgres_volume:-lumefy_postgres_data}}
BACKEND_STATIC_VOLUME=${BACKEND_STATIC_VOLUME:-${configured_static_volume:-lumefy_backend_static}}
export POSTGRES_VOLUME_NAME BACKEND_STATIC_VOLUME

for volume_name in "$POSTGRES_VOLUME_NAME" "$BACKEND_STATIC_VOLUME"; do
  case "$volume_name" in
    ""|[-._]*|*[!a-zA-Z0-9_.-]*)
      echo "Refusing an invalid Docker volume name: $volume_name" >&2
      exit 1
      ;;
  esac
done

compose config --quiet

if docker volume inspect "$POSTGRES_VOLUME_NAME" >/dev/null 2>&1 \
  && docker volume inspect "$BACKEND_STATIC_VOLUME" >/dev/null 2>&1; then
  if ! docker compose --env-file "$ROOT_ENV_FILE" -f "$COMPOSE_FILE" \
    ps --status running --services | grep -qx db; then
    echo "Existing production data found, but PostgreSQL is not running; refusing an unbacked deployment." >&2
    exit 1
  fi
  sh scripts/backup-production.sh
elif docker volume inspect "$POSTGRES_VOLUME_NAME" >/dev/null 2>&1 \
  || docker volume inspect "$BACKEND_STATIC_VOLUME" >/dev/null 2>&1; then
  echo "Only part of the production data volumes exists; refusing an ambiguous deployment." >&2
  exit 1
else
  echo "No production data volumes found; treating this as the initial deployment."
fi

build_services=""
changed_files=""

add_build_service() {
  case " $build_services " in
    *" $1 "*) ;;
    *) build_services="$build_services $1" ;;
  esac
}

# Rebuild only the image(s) affected by this revision.  Every deploy used to
# rebuild Angular, the storefront and the backend on the VPS, even when only
# one of them changed.  Keeping the previous revision's image under its own
# immutable tag lets us reuse the other services without sacrificing rollback.
if [ "$PREVIOUS_REVISION" != "unknown" ] && git cat-file -e "$PREVIOUS_REVISION^{commit}" 2>/dev/null; then
  changed_files=$(git diff --name-only "$PREVIOUS_REVISION" HEAD || true)
  printf '%s\n' "Changed files since $PREVIOUS_REVISION:"
  printf '%s\n' "$changed_files"

  case "$changed_files" in
    *"docker-compose.prod.yml"*)
      build_services="backend frontend storefront"
      ;;
    *)
      case "$changed_files" in *"backend/"*) add_build_service backend ;; esac
      case "$changed_files" in *"frontend_mantis/"*) add_build_service frontend ;; esac
      case "$changed_files" in *"storefront_nextmerce/"*) add_build_service storefront ;; esac
      ;;
  esac
fi

if [ -z "$build_services" ] && [ "$PREVIOUS_REVISION" = "unknown" ]; then
  build_services="backend frontend storefront"
fi

if [ -n "$build_services" ]; then
  printf '%s\n' "Building affected services:$build_services"
  # shellcheck disable=SC2086
  compose build --pull $build_services
else
  printf '%s\n' "No application image changes detected; reusing previous images."
fi

for service in backend frontend storefront; do
  case " $build_services " in
    *" $service "*)
      continue
      ;;
  esac

  previous_image="lumefy-$service:$PREVIOUS_REVISION"
  current_image="lumefy-$service:$LUMEFY_IMAGE_TAG"
  if ! docker image inspect "$previous_image" >/dev/null 2>&1; then
    echo "Cannot reuse missing image $previous_image; rebuilding $service." >&2
    # shellcheck disable=SC2086
    compose build --pull "$service"
    continue
  fi
  docker tag "$previous_image" "$current_image"
  printf '%s\n' "Reusing $previous_image as $current_image"
done

# Validate application settings before Compose replaces any running service.
# This catches missing production secrets without turning a configuration error
# into an outage.
compose run --rm --no-deps migrate python -c \
  "from app.core.config import settings; assert settings.ENVIRONMENT.lower() == 'production'"

if ! compose up -d --remove-orphans --wait --wait-timeout 180; then
  show_deploy_diagnostics
  exit 1
fi
sh scripts/smoke-production.sh

mkdir -p backups/deployments
printf '%s\n' "$PREVIOUS_REVISION" > backups/deployments/previous-revision
printf '%s\n' "$(git rev-parse HEAD)" > backups/deployments/current-revision

echo "Deployment completed: $(git rev-parse HEAD)"
