import sqlite3
import psycopg2
 
SQLITE_DB = "scrapers/nabdh.db"
PG_URL = "postgresql://postgres:qeDBpjpLwJWdooDBtEtmFzWEWphKBgKM@hayabusa.proxy.rlwy.net:51253/railway"
 
# اقرأ البيانات من SQLite
sqlite_conn = sqlite3.connect(SQLITE_DB)
sqlite_conn.row_factory = sqlite3.Row
rows = sqlite_conn.execute("SELECT * FROM jobs").fetchall()
jobs = [dict(r) for r in rows]
sqlite_conn.close()
 
print(f"وجدنا {len(jobs)} وظيفة في SQLite")
 
# اتصل بـ PostgreSQL
pg_conn = psycopg2.connect(PG_URL)
cur = pg_conn.cursor()
 
# أنشئ الجدول
cur.execute("""
CREATE TABLE IF NOT EXISTS jobs (
    id SERIAL PRIMARY KEY,
    title TEXT,
    company TEXT,
    city TEXT,
    open_positions INTEGER,
    source TEXT,
    url TEXT,
    created_at TIMESTAMP DEFAULT NOW()
)
""")
 
# أدخل البيانات
for job in jobs:
    cur.execute("""
        INSERT INTO jobs (title, company, city, open_positions, source, url)
        VALUES (%s, %s, %s, %s, %s, %s)
    """, (
        job.get("title"),
        job.get("company"),
        job.get("city"),
        job.get("open_positions"),
        job.get("source"),
        job.get("url"),
    ))
 
pg_conn.commit()
cur.close()
pg_conn.close()
 
print("✅ تم ترحيل البيانات بنجاح!")