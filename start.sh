#!/bin/bash
set -e

echo "========================================="
echo "   MediFlow Backend - Starting Server"
echo "========================================="

# Wait for database to be ready
echo "Waiting for database..."
for i in {1..30}; do
    python -c "
from sqlalchemy import create_engine, text
import os
db_url = os.getenv('DATABASE_URL', '')
if db_url.startswith('postgres://'):
    db_url = db_url.replace('postgres://', 'postgresql://', 1)
engine = create_engine(db_url)
with engine.connect() as conn:
    conn.execute(text('SELECT 1'))
" 2>/dev/null && break
    echo "  Attempt $i/30 - database not ready, waiting..."
    sleep 1
done

# Run database migrations FIRST
echo "Running database migrations..."
if alembic upgrade head; then
    echo "Migrations complete."
else
    echo "WARNING: Alembic migrations failed. Attempting fallback schema creation."
    python - <<'PY'
import os
from app.core.database import Base, engine
print('Creating missing tables via SQLAlchemy metadata...')
# This will safely build everything if Alembic crapped out
Base.metadata.create_all(bind=engine)
print('Fallback schema creation complete.')
PY
    echo "WARNING: Migrations failed, but fallback create_all was executed."
    echo "  Fix your Alembic migration chain to apply schema changes properly."
fi

# Manual Schema Sync (Safe adjustment after tables are created)
echo "Ensuring database schema column modifications match..."
python - <<'PY'
import os
from sqlalchemy import create_engine, text
try:
    database_url = os.getenv('DATABASE_URL')
    if database_url and database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql://", 1)
    engine = create_engine(database_url)
    with engine.connect() as conn:
        print("Running manual column synchronization adjustments...")
        
        # Check if referrals table exists before attempting alter commands
        table_check = conn.execute(text("SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'referrals')")).scalar()
        
        if table_check:
            conn.execute(text("ALTER TABLE referrals ADD COLUMN IF NOT EXISTS accepted_by INTEGER"))
            conn.execute(text("ALTER TABLE referrals ADD COLUMN IF NOT EXISTS rejected_by INTEGER"))
            conn.execute(text("ALTER TABLE referrals ADD COLUMN IF NOT EXISTS completed_by INTEGER"))
            conn.execute(text("ALTER TABLE referrals ADD COLUMN IF NOT EXISTS completed_at TIMESTAMP WITH TIME ZONE"))
            conn.commit()
            print("Manual column synchronization complete.")
        else:
            print("Skipping column adjustments: 'referrals' table does not exist yet.")
except Exception as e:
    print(f"Warning: Manual schema sync failed: {e}")
PY

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