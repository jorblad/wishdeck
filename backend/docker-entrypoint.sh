#!/usr/bin/env sh
# Production entrypoint: apply Alembic migrations, then start the API.
# This makes deploys/upgrades hands-free (no manual `alembic upgrade`).
#
# In development the container relies on the app's idempotent create_all
# (init_db), so we skip Alembic to avoid conflicting with that on the
# mounted dev database.
set -e

if [ "${ENVIRONMENT:-production}" != "development" ]; then
  echo "Running database migrations..."
  alembic upgrade head
else
  echo "Development mode: skipping Alembic (using create_all)."
fi

echo "Starting API..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
