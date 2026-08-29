#!/usr/bin/env sh
set -eu

# The caller must first check out the exact reviewed commit. In CI this script
# receives GITHUB_SHA as LUMEFY_IMAGE_TAG, keeping each release image addressable.
# Per-service tags prevent Compose from recreating healthy, unchanged upstreams.
COMPOSE_FILE=${COMPOSE_FILE:-docker-compose.prod.yml}
ROOT_ENV_FILE=${ROOT_ENV_FILE:-.env.production}
BACKEND_ENV_FILE=${BACKEND_ENV_FILE:-./backend/.env.production}
LUMEFY_IMAGE_TAG=${LUMEFY_IMAGE_TAG:-$(git rev-parse --short=12 HEAD)}
PREVIOUS_REVISION=${PREVIOUS_REVISION:-unknown}
BACKEND_IMAGE_TAG=${BACKEND_IMAGE_TAG:-$LUMEFY_IMAGE_TAG}
FRONTEND_IMAGE_TAG=${FRONTEND_IMAGE_TAG:-$LUMEFY_IMAGE_TAG}
STOREFRONT_IMAGE_TAG=${STOREFRONT_IMAGE_TAG:-$LUMEFY_IMAGE_TAG}

export COMPOSE_FILE ROOT_ENV_FILE BACKEND_ENV_FILE LUMEFY_IMAGE_TAG \
  BACKEND_IMAGE_TAG FRONTEND_IMAGE_TAG STOREFRONT_IMAGE_TAG

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
configured_deploy_backup_dir=$(read_root_env DEPLOY_BACKUP_DIR)
configured_deploy_backup_retention=$(read_root_env DEPLOY_BACKUP_RETENTION_DAYS)
POSTGRES_VOLUME_NAME=${POSTGRES_VOLUME_NAME:-${configured_postgres_volume:-lumefy_postgres_data}}
BACKEND_STATIC_VOLUME=${BACKEND_STATIC_VOLUME:-${configured_static_volume:-lumefy_backend_static}}
DEPLOY_BACKUP_DIR=${DEPLOY_BACKUP_DIR:-${configured_deploy_backup_dir:-./backups/pre-deploy}}
DEPLOY_BACKUP_RETENTION_DAYS=${DEPLOY_BACKUP_RETENTION_DAYS:-${configured_deploy_backup_retention:-7}}
export POSTGRES_VOLUME_NAME BACKEND_STATIC_VOLUME DEPLOY_BACKUP_DIR DEPLOY_BACKUP_RETENTION_DAYS

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
  BACKUP_MODE=database \
    BACKUP_DIR="$DEPLOY_BACKUP_DIR" \
    BACKUP_RETENTION_DAYS="$DEPLOY_BACKUP_RETENTION_DAYS" \
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

service_is_built() {
  case " $build_services " in
    *" $1 "*) return 0 ;;
    *) return 1 ;;
  esac
}

set_service_tag() {
  service=$1
  tag=$2
  case "$service" in
    backend) BACKEND_IMAGE_TAG=$tag ;;
    frontend) FRONTEND_IMAGE_TAG=$tag ;;
    storefront) STOREFRONT_IMAGE_TAG=$tag ;;
    *)
      echo "Unknown application service: $service" >&2
      exit 1
      ;;
  esac
  export BACKEND_IMAGE_TAG FRONTEND_IMAGE_TAG STOREFRONT_IMAGE_TAG
}

get_service_tag() {
  case "$1" in
    backend) printf '%s\n' "$BACKEND_IMAGE_TAG" ;;
    frontend) printf '%s\n' "$FRONTEND_IMAGE_TAG" ;;
    storefront) printf '%s\n' "$STOREFRONT_IMAGE_TAG" ;;
    *) return 1 ;;
  esac
}

running_service_tag() {
  service=$1
  container_id=$(compose ps -q "$service" 2>/dev/null || true)
  test -n "$container_id" || return 1
  image_ref=$(docker inspect --format '{{.Config.Image}}' "$container_id" 2>/dev/null || true)
  case "$image_ref" in
    "lumefy-$service:"*) printf '%s\n' "${image_ref#lumefy-$service:}" ;;
    *) return 1 ;;
  esac
}

discover_proxy_container() {
  configured_proxy_container=$(read_root_env PROXY_CONTAINER_NAME)
  if [ -n "$configured_proxy_container" ] \
    && docker container inspect "$configured_proxy_container" >/dev/null 2>&1; then
    printf '%s\n' "$configured_proxy_container"
    return 0
  fi

  configured_proxy_network=$(read_root_env PROXY_NETWORK)
  proxy_network=${PROXY_NETWORK:-${configured_proxy_network:-npm_default}}
  docker network inspect "$proxy_network" >/dev/null 2>&1 || return 1
  for candidate in $(docker network inspect "$proxy_network" \
    --format '{{range .Containers}}{{println .Name}}{{end}}'); do
    candidate_image=$(docker inspect --format '{{.Config.Image}}' "$candidate" 2>/dev/null || true)
    case "$candidate_image" in
      *nginx-proxy-manager*)
        printf '%s\n' "$candidate"
        return 0
        ;;
    esac
  done
  return 1
}

reload_external_proxy() {
  proxy_container=$(discover_proxy_container || true)
  if [ -z "$proxy_container" ]; then
    echo "Nginx Proxy Manager container was not found; public smoke test will verify routing." >&2
    return 0
  fi

  if docker exec "$proxy_container" nginx -t \
    && docker exec "$proxy_container" nginx -s reload; then
    echo "Reloaded Nginx Proxy Manager after upstream changes: $proxy_container"
  else
    echo "Could not reload Nginx Proxy Manager; public smoke test will verify routing." >&2
  fi
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

# Resolve unchanged services to the exact image reference already running.
# Merely retagging every image with the new revision made Compose recreate every
# upstream and left Nginx Proxy Manager pointing at stale container addresses.
for service in backend frontend storefront; do
  if service_is_built "$service"; then
    set_service_tag "$service" "$LUMEFY_IMAGE_TAG"
    continue
  fi

  reusable_tag=$(running_service_tag "$service" || true)
  if [ -z "$reusable_tag" ] \
    && [ "$PREVIOUS_REVISION" != "unknown" ] \
    && docker image inspect "lumefy-$service:$PREVIOUS_REVISION" >/dev/null 2>&1; then
    reusable_tag=$PREVIOUS_REVISION
  fi

  if [ -z "$reusable_tag" ]; then
    echo "No reusable image found for $service; rebuilding it." >&2
    add_build_service "$service"
    set_service_tag "$service" "$LUMEFY_IMAGE_TAG"
  else
    set_service_tag "$service" "$reusable_tag"
  fi
done

printf '%s\n' "Selected image tags: backend=$BACKEND_IMAGE_TAG frontend=$FRONTEND_IMAGE_TAG storefront=$STOREFRONT_IMAGE_TAG"

if [ -n "$build_services" ]; then
  printf '%s\n' "Building affected services:$build_services"
  # shellcheck disable=SC2086
  compose build --pull $build_services
else
  printf '%s\n' "No application image changes detected; reusing previous images."
fi

for service in backend frontend storefront; do
  service_is_built "$service" && continue
  reusable_tag=$(get_service_tag "$service")
  previous_image="lumefy-$service:$reusable_tag"
  current_image="lumefy-$service:$LUMEFY_IMAGE_TAG"
  if ! docker image inspect "$previous_image" >/dev/null 2>&1; then
    echo "Reusable image disappeared before rollout: $previous_image" >&2
    exit 1
  fi
  docker tag "$previous_image" "$current_image"
  printf '%s\n' "Keeping $previous_image running; recorded rollback alias $current_image"
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
if [ -n "$build_services" ]; then
  reload_external_proxy
fi
sh scripts/smoke-public.sh

mkdir -p backups/deployments
printf '%s\n' "$PREVIOUS_REVISION" > backups/deployments/previous-revision
printf '%s\n' "$(git rev-parse HEAD)" > backups/deployments/current-revision

echo "Deployment completed: $(git rev-parse HEAD)"
