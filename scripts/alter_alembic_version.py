import os
from sqlalchemy import create_engine, text

url = os.getenv('DATABASE_URL')
if not url:
    print('DATABASE_URL not set')
    raise SystemExit(1)
engine = create_engine(url)
with engine.connect() as conn:
    conn.execute(text("ALTER TABLE alembic_version ALTER COLUMN version_num TYPE VARCHAR(128);"))
    print('altered alembic_version.version_num to VARCHAR(128)')
