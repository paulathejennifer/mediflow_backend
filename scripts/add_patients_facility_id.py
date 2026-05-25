import os
from sqlalchemy import create_engine, text
url = os.getenv('DATABASE_URL')
if not url:
    print('DATABASE_URL not set')
    raise SystemExit(1)
print('Using DATABASE_URL:', (url[:80] + '...' if len(url) > 80 else url))
engine = create_engine(url)
with engine.connect() as conn:
    res = conn.execute(text("select column_name from information_schema.columns where table_name='patients' and column_name='facility_id'")).fetchone()
    if res:
        print('patients.facility_id already exists')
    else:
        print('adding patients.facility_id column...')
        conn.execute(text('ALTER TABLE patients ADD COLUMN facility_id integer'))
        conn.execute(text('CREATE INDEX IF NOT EXISTS ix_patients_facility_id ON patients(facility_id)'))
        print('added column and index')
