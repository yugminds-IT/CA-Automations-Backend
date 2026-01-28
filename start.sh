#!/bin/bash
set -e

echo "🚀 Starting Backend CAA API..."

# Run database migrations
echo "📦 Running database migrations..."
alembic upgrade head

# Start the application
echo "✅ Starting uvicorn server..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
