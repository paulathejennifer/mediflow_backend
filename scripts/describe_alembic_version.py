import os
from sqlalchemy import create_engine, text
url = os.getenv('DATABASE_URL')
if not url:
    print('DATABASE_URL not set')
    raise SystemExit(1)
engine = create_engine(url)
with engine.connect() as conn:
    r = conn.execute(text("select column_name, data_type, character_maximum_length from information_schema.columns where table_name='alembic_version'"))
    for row in r:
        print(row)
    v = conn.execute(text("select version_num from alembic_version")).scalar()
    print('current version_num:', v)
