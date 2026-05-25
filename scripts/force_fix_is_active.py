import os
import psycopg2

DATABASE_URL = os.environ.get("DATABASE_URL")
if not DATABASE_URL:
    raise SystemExit("DATABASE_URL not set")

print("Connecting to:", DATABASE_URL)
conn = psycopg2.connect(DATABASE_URL)
cur = conn.cursor()
print("Running ALTER TABLE to cast is_active to boolean...")
cur.execute("ALTER TABLE users ALTER COLUMN is_active TYPE boolean USING (is_active::boolean)")
conn.commit()
print("Alter completed. Fetching column types...")
cur.execute("select column_name, data_type from information_schema.columns where table_name='users' order by ordinal_position")
rows = cur.fetchall()
print(rows)
cur.close()
conn.close()
