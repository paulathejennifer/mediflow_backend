import os
from sqlalchemy import create_engine, text
url = os.getenv('DATABASE_URL')
if not url:
    print('DATABASE_URL not set')
    raise SystemExit(1)
engine = create_engine(url)
with engine.connect() as conn:
    conn.execute(text("UPDATE alembic_version SET version_num='008_add_updated_at_to_patient_identifiers'"))
    print('alembic_version set to 008_add_updated_at_to_patient_identifiers')
    v = conn.execute(text("select version_num from alembic_version")).scalar()
    print('now:', v)
