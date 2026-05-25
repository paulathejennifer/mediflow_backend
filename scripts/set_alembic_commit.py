import os
from sqlalchemy import create_engine, text
url = os.getenv('DATABASE_URL')
engine = create_engine(url)
with engine.connect() as conn:
    conn.execute(text('BEGIN'))
    conn.execute(text("UPDATE alembic_version SET version_num='008_add_updated_at_to_patient_identifiers'"))
    conn.execute(text('COMMIT'))
    v = conn.execute(text('select version_num from alembic_version')).scalar()
    print('alembic_version now:', v)
