#!/usr/bin/env sh
set -eu

ROOT_ENV_FILE=${ROOT_ENV_FILE:-.env.production}
PUBLIC_SMOKE_ATTEMPTS=${PUBLIC_SMOKE_ATTEMPTS:-6}
PUBLIC_SMOKE_DELAY_SECONDS=${PUBLIC_SMOKE_DELAY_SECONDS:-5}

test -s "$ROOT_ENV_FILE"

read_root_env() {
  key=$1
  sed -n "s/^${key}=//p" "$ROOT_ENV_FILE" | tail -n 1 | tr -d '\r'
}

admin_domain=$(read_root_env ADMIN_DOMAIN)
if [ -z "$admin_domain" ] && [ -z "${PUBLIC_SMOKE_BASE_URL:-}" ]; then
  echo "ADMIN_DOMAIN or PUBLIC_SMOKE_BASE_URL is required for public smoke checks." >&2
  exit 1
fi
PUBLIC_SMOKE_BASE_URL=${PUBLIC_SMOKE_BASE_URL:-https://$admin_domain}
PUBLIC_SMOKE_BASE_URL=${PUBLIC_SMOKE_BASE_URL%/}

case "$PUBLIC_SMOKE_BASE_URL" in
  https://*) ;;
  *)
    echo "PUBLIC_SMOKE_BASE_URL must use HTTPS: $PUBLIC_SMOKE_BASE_URL" >&2
    exit 1
    ;;
esac

case "$PUBLIC_SMOKE_ATTEMPTS" in
  *[!0-9]*|""|0)
    echo "PUBLIC_SMOKE_ATTEMPTS must be a positive integer." >&2
    exit 1
    ;;
esac

case "$PUBLIC_SMOKE_DELAY_SECONDS" in
  *[!0-9]*|"")
    echo "PUBLIC_SMOKE_DELAY_SECONDS must be a non-negative integer." >&2
    exit 1
    ;;
esac

probe_status() {
  url=$1
  curl --silent --show-error \
    --connect-timeout 10 \
    --max-time 30 \
    --output /dev/null \
    --write-out '%{http_code}' \
    "$url"
}

attempt=1
while [ "$attempt" -le "$PUBLIC_SMOKE_ATTEMPTS" ]; do
  cache_buster=$(date +%s)
  admin_status=$(probe_status "$PUBLIC_SMOKE_BASE_URL/?deployment-smoke=$cache_buster" || printf '000')
  api_status=$(probe_status "$PUBLIC_SMOKE_BASE_URL/api/v1/readyz?deployment-smoke=$cache_buster" || printf '000')
  static_status=$(probe_status "$PUBLIC_SMOKE_BASE_URL/static/deployment-smoke-missing-$cache_buster" || printf '000')

  if [ "$admin_status" = "200" ] \
    && [ "$api_status" = "200" ] \
    && [ "$static_status" = "404" ]; then
    echo "Public production smoke checks passed: admin=200 api-ready=200 static=404"
    exit 0
  fi

  echo "Public smoke attempt $attempt/$PUBLIC_SMOKE_ATTEMPTS failed: admin=$admin_status api=$api_status static=$static_status" >&2
  if [ "$attempt" -lt "$PUBLIC_SMOKE_ATTEMPTS" ]; then
    sleep "$PUBLIC_SMOKE_DELAY_SECONDS"
  fi
  attempt=$((attempt + 1))
done

echo "Public production routing is unhealthy: $PUBLIC_SMOKE_BASE_URL" >&2
exit 1
