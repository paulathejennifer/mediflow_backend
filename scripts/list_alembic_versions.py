import os
from sqlalchemy import create_engine, text
url = os.getenv('DATABASE_URL')
engine = create_engine(url)
with engine.connect() as conn:
    rows = conn.execute(text("select table_schema, table_name from information_schema.tables where table_name='alembic_version' order by table_schema")).fetchall()
    print('alembic_version tables:')
    for s,t in rows:
        print('-', s, t)
        try:
            v = conn.execute(text(f"select version_num from {s}.alembic_version")).scalar()
        except Exception as e:
            v = f'error: {e}'
        print('  ->', v)
