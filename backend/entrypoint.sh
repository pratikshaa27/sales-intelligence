#!/bin/sh
set -e

echo "Waiting for database migrations..."
alembic upgrade head

echo "Starting API server..."
exec "$@"
