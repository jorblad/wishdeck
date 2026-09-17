#!/usr/bin/env sh
# Production entrypoint: apply Alembic migrations, then start the API.
# This makes deploys/upgrades hands-free (no manual `alembic upgrade`).
#
# In development we also run Alembic so schema changes (new columns, etc.)
# are applied automatically. If an older dev DB has tables but no
# alembic_version record, we stamp it to the current head first.
set -e

if [ "${ENVIRONMENT:-production}" = "development" ]; then
  echo "Development mode: applying Alembic migrations..."
  if ! alembic current >/dev/null 2>&1; then
    echo "No Alembic revision tracked; stamping current head..."
    alembic stamp head || true
  fi
  alembic upgrade head
else
  echo "Running database migrations..."
  alembic upgrade head
fi

echo "Starting API..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
