#!/usr/bin/env sh
set -eu

echo "backup-postgres.sh now creates a complete production backup (database + uploads)."
exec sh "$(dirname "$0")/backup-production.sh"
