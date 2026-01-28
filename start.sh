#!/bin/bash
# Production startup: wait for DB, run migrations with retries, then start uvicorn.
# Avoids restart loops when DB is not ready at container start (e.g. Coolify).

set -e

echo "Starting Backend CAA API..."

# 1. Wait for database to be reachable
if [ -n "${DATABASE_URL}" ]; then
  echo "Waiting for database..."
  python scripts/wait_for_db.py || exit 1
else
  echo "DATABASE_URL not set; skipping DB wait."
fi

# 2. Run migrations with retries (DB may be ready but still initializing)
MIGRATION_ATTEMPTS="${MIGRATION_MAX_ATTEMPTS:-5}"
MIGRATION_DELAY="${MIGRATION_RETRY_DELAY_SECONDS:-5}"
attempt=1

while [ "$attempt" -le "$MIGRATION_ATTEMPTS" ]; do
  echo "Running migrations (attempt $attempt/$MIGRATION_ATTEMPTS)..."
  if alembic upgrade head; then
    echo "Migrations completed successfully."
    break
  fi
  if [ "$attempt" -eq "$MIGRATION_ATTEMPTS" ]; then
    echo "Migrations failed after $MIGRATION_ATTEMPTS attempts. Exiting."
    exit 1
  fi
  echo "Migration attempt $attempt failed. Retrying in ${MIGRATION_DELAY}s..."
  sleep "$MIGRATION_DELAY"
  attempt=$((attempt + 1))
done

# 3. Start the application
echo "Starting uvicorn server on 0.0.0.0:8000..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
