#!/bin/sh
# Restores a backup produced by ./scripts/backup.sh into a target database. Defaults to
# restoring into "<POSTGRES_DB>_restore_test" rather than clobbering the real database, so the
# normal way to use this script is *as the backup-restoration test itself*: back up, restore
# into the scratch database, verify, then decide separately (and deliberately) whether to ever
# restore over a real database.
#
# Usage:
#   ./scripts/restore.sh backups/20260101_120000.sql.gz                # restores into the scratch DB
#   ./scripts/restore.sh backups/20260101_120000.sql.gz sales_intelligence  # restores into a named DB (destructive!)
set -eu

DUMP_FILE="${1:?Usage: $0 <path-to-backup.sql.gz> [target-database-name]}"
SERVICE="${SERVICE:-postgres}"
COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.yml}"

if [ -f .env ]; then
  set -a
  # shellcheck disable=SC1091
  . ./.env
  set +a
fi
POSTGRES_USER="${POSTGRES_USER:-postgres}"
DEFAULT_TARGET="${POSTGRES_DB:-sales_intelligence}_restore_test"
TARGET_DB="${2:-$DEFAULT_TARGET}"

if [ ! -f "$DUMP_FILE" ]; then
  echo "Backup file not found: $DUMP_FILE" >&2
  exit 1
fi

echo "Restoring $DUMP_FILE into database '$TARGET_DB' on service '$SERVICE' ..."
docker compose -f "$COMPOSE_FILE" exec -T "$SERVICE" \
  psql -U "$POSTGRES_USER" -d postgres -v ON_ERROR_STOP=1 \
  -c "DROP DATABASE IF EXISTS \"$TARGET_DB\";" \
  -c "CREATE DATABASE \"$TARGET_DB\";"

gunzip -c "$DUMP_FILE" | docker compose -f "$COMPOSE_FILE" exec -T "$SERVICE" \
  psql -U "$POSTGRES_USER" -d "$TARGET_DB" -v ON_ERROR_STOP=1 --quiet

echo "Restored into '$TARGET_DB'. Spot-check row counts, e.g.:"
echo "  docker compose -f $COMPOSE_FILE exec $SERVICE psql -U $POSTGRES_USER -d $TARGET_DB -c 'select count(*) from organizations;'"
