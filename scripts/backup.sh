#!/bin/sh
# Dumps the running docker-compose postgres database to backups/<timestamp>.sql.gz.
# Usage: ./scripts/backup.sh [compose-project-postgres-service-name]
#
# Restoring is the part that actually proves a backup is worth anything (spec §23 "Backup
# restoration testing") — see ./scripts/restore.sh, which this pair is designed to round-trip
# with (verified together, not just written and left untested).
set -eu

SERVICE="${1:-postgres}"
COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.yml}"
BACKUP_DIR="$(dirname "$0")/../backups"
TIMESTAMP="$(date +%Y%m%d_%H%M%S)"
OUT_FILE="$BACKUP_DIR/${TIMESTAMP}.sql.gz"

mkdir -p "$BACKUP_DIR"

# Read the same POSTGRES_* values docker-compose itself uses, so this always backs up the
# database actually running under compose rather than requiring them to be re-specified here.
if [ -f .env ]; then
  set -a
  # shellcheck disable=SC1091
  . ./.env
  set +a
fi
POSTGRES_USER="${POSTGRES_USER:-postgres}"
POSTGRES_DB="${POSTGRES_DB:-sales_intelligence}"

echo "Backing up database '$POSTGRES_DB' from service '$SERVICE' to $OUT_FILE ..."
docker compose -f "$COMPOSE_FILE" exec -T "$SERVICE" \
  pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" --format=plain --no-owner --no-privileges \
  | gzip > "$OUT_FILE"

echo "Done: $OUT_FILE ($(du -h "$OUT_FILE" | cut -f1))"
