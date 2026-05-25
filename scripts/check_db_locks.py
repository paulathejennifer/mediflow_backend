import os
import psycopg2

DATABASE_URL = os.environ.get("DATABASE_URL")
if not DATABASE_URL:
    raise SystemExit("DATABASE_URL not set")

conn = psycopg2.connect(DATABASE_URL)
cur = conn.cursor()
print('Current pg_stat_activity rows (non-idle):')
cur.execute("select pid, usename, state, query_start, wait_event, query from pg_stat_activity where state <> 'idle' order by query_start desc limit 20")
rows = cur.fetchall()
for r in rows:
    print(r)

print('\nLocks related to relation users:')
cur.execute("select l.locktype, l.mode, l.granted, a.pid, a.query from pg_locks l left join pg_stat_activity a on l.pid = a.pid where relation = (select oid from pg_class where relname = 'users')")
rows = cur.fetchall()
for r in rows:
    print(r)

cur.close()
conn.close()
