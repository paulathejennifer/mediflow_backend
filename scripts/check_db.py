import os
from sqlalchemy import create_engine, text

url = os.getenv("DATABASE_URL")
if not url:
    print("DATABASE_URL not set")
    raise SystemExit(1)

print("Using DATABASE_URL:", url[:60] + "..." if len(url) > 60 else url)
engine = create_engine(url)
with engine.connect() as conn:
    # alembic_version
    try:
        res = conn.execute(text('select version_num from alembic_version'))
        row = res.fetchone()
        print('alembic_version:', row[0] if row else None)
    except Exception as e:
        print('alembic_version: error -', e)

    # refresh_tokens
    try:
        r = conn.execute(text("select to_regclass('public.refresh_tokens')")).scalar()
        print('refresh_tokens present:', r)
    except Exception as e:
        print('refresh_tokens check error -', e)
