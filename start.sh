#!/bin/bash
set -e

echo "========================================="
echo "  MediFlow Backend - Starting Server"
echo "========================================="

# Wait for database to be ready
echo "Waiting for database..."
for i in {1..30}; do
    python -c "
from sqlalchemy import create_engine, text
import os
engine = create_engine(os.getenv('DATABASE_URL'))
with engine.connect() as conn:
    conn.execute(text('SELECT 1'))
    print('Database is ready!')
" 2>/dev/null && break
    echo "  Attempt $i/30 - database not ready, waiting..."
    sleep 2
done

# Run database migrations
echo "Running database migrations..."
alembic upgrade head
echo "Migrations complete."

# Create upload directory if it doesn't exist
mkdir -p "${UPLOAD_DIR:-uploads}"

# Start server
echo "Starting MediFlow Backend..."
if [ "${ENVIRONMENT}" = "development" ]; then
    echo "Mode: Development (uvicorn with reload)"
    exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}" --reload
else
    echo "Mode: Production (gunicorn + uvicorn workers)"
    exec gunicorn app.main:app -c gunicorn.conf.py
fi
