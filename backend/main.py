from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
import psycopg2
import psycopg2.extras
from collections import Counter
import os

app = FastAPI(title="Nabdh API")
 
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)
 
DATABASE_URL = os.environ.get("DATABASE_URL")
 
def get_connection():
    return psycopg2.connect(DATABASE_URL)
 
def get_jobs(city=None, sector=None):
    conn = get_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    q = "SELECT * FROM jobs WHERE 1=1"
    params = []
    if city:
        q += " AND city ILIKE %s"
        params.append(f"%{city}%")
    if sector:
        q += " AND company ILIKE %s"
        params.append(f"%{sector}%")
    cur.execute(q, params)
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]
 
@app.get("/")
def root():
    return {"status": "Nabdh API running"}
 
@app.get("/api/top-roles")
def top_roles(city: str = None, sector: str = None, limit: int = 10):
    jobs = get_jobs(city, sector)
    titles = [j["title"] for j in jobs if j["title"]]
    counts = Counter(titles).most_common(limit)
    return [{"role": r, "count": c} for r, c in counts]
 
@app.get("/api/top-cities")
def top_cities(limit: int = 10):
    jobs = get_jobs()
    cities = [j["city"] for j in jobs if j["city"]]
    counts = Counter(cities).most_common(limit)
    return [{"city": c, "count": n} for c, n in counts]
 
@app.get("/api/top-companies")
def top_companies(city: str = None, limit: int = 10):
    jobs = get_jobs(city)
    companies = [j["company"] for j in jobs if j["company"]]
    counts = Counter(companies).most_common(limit)
    return [{"company": c, "count": n} for c, n in counts]
 
@app.get("/api/open-positions")
def open_positions(city: str = None):
    jobs = get_jobs(city)
    total = sum(j["open_positions"] or 1 for j in jobs)
    return {"total_open_positions": total, "total_jobs": len(jobs)}
 
@app.get("/api/jobs")
def list_jobs(city: str = None, sector: str = None, limit: int = 50):
    jobs = get_jobs(city, sector)
    return jobs[:limit]
 
@app.get("/api/role/{role_name}")
def role_detail(role_name: str):
    jobs = get_jobs()
    role_jobs = [j for j in jobs if j["title"] == role_name]
    if not role_jobs:
        return {"role": role_name, "count": 0, "skills": [], "cities": [], "companies": []}
    cities = Counter([j["city"] for j in role_jobs if j["city"]]).most_common(5)
    companies = Counter([j["company"] for j in role_jobs if j["company"]]).most_common(5)
    return {
        "role": role_name,
        "count": len(role_jobs),
        "cities": [{"city": c, "count": n} for c, n in cities],
        "companies": [{"company": c, "count": n} for c, n in companies],
    }