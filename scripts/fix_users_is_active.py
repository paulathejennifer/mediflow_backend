import os
from sqlalchemy import create_engine, text

url = os.getenv('DATABASE_URL')
if not url:
    print('DATABASE_URL not set')
    raise SystemExit(1)

engine = create_engine(url)
with engine.connect() as conn:
    print('Current distinct values:')
    rows = conn.execute(text("select distinct is_active from users")).fetchall()
    print(rows)
    print('Altering users.is_active to boolean...')
    conn.execute(text("ALTER TABLE users ALTER COLUMN is_active TYPE boolean USING (is_active::boolean);"))
    print('Altered.')
    rows = conn.execute(text("select column_name, data_type from information_schema.columns where table_name='users' and column_name='is_active'")).fetchall()
    print(rows)
