import os
from sqlalchemy import create_engine, text
url = os.getenv('DATABASE_URL')
if not url:
    print('DATABASE_URL not set')
    raise SystemExit(1)
engine = create_engine(url)
with engine.connect() as conn:
    conn.execute(text('BEGIN'))
    conn.execute(text("ALTER TABLE alembic_version ALTER COLUMN version_num TYPE VARCHAR(128);"))
    conn.execute(text('COMMIT'))
    print('altered with explicit commit')
    r = conn.execute(text("select character_maximum_length from information_schema.columns where table_name='alembic_version' and column_name='version_num'")).scalar()
    print('new length:', r)
