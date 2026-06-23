from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
import sqlite3
import re
from datetime import datetime

import time
 
 
# ─── Database ─────────────────────────────────────────────────────
 
def init_db(db_path="nabdh.db"):
    conn = sqlite3.connect(db_path)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS jobs (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            title          TEXT,
            company        TEXT,
            city           TEXT,
            open_positions INTEGER,
            post_date      TEXT,
            source         TEXT DEFAULT 'jadarat',
            scraped_at     TEXT
        )
    """)
    conn.commit()
    return conn
 
 
# ─── Parser ───────────────────────────────────────────────────────
 
def parse_card(card):
    texts = [s.get_text(strip=True) for s in card.find_all("span")
             if s.get_text(strip=True)]
 
    # المسمى الوظيفي — يظهر قبل "Job title based on the contract"
    title = ""
    for i, t in enumerate(texts):
        if "Job title based on the contract" in t and i > 0:
            title = texts[i - 1]
            break
 
    # الشركة — النص العربي الأول (صاحب العمل)
    company = ""
    for t in texts:
        if re.search(r'[\u0600-\u06FF]', t) and len(t) > 5:
            company = t
            break
 
    # المدينة — أول نص يبدأ بـ AL أو اسم مدينة معروف
    KNOWN_CITIES = {"Riyadh", "Jeddah", "Dammam", "Mecca", "Medina",
                    "Khobar", "Tabuk", "Abha", "Taif", "Hail"}
    city = ""
    for t in texts:
        if t.startswith("AL ") or t in KNOWN_CITIES:
            city = t
            break
 
    # عدد الوظائف المتاحة — أول رقم منفرد
    open_positions = None
    for t in texts:
        if re.fullmatch(r'\d{1,3}', t):
            open_positions = int(t)
            break
 
    # تاريخ النشر — تنسيق هجري dd/mm/14xx
    post_date = ""
    for t in texts:
        if re.match(r'\d{1,2}/\d{1,2}/14\d{2}', t):
            post_date = t
            break
 
    return {
        "title":          title,
        "company":        company,
        "city":           city,
        "open_positions": open_positions,
        "post_date":      post_date,
        "source":         "jadarat",
        "scraped_at":     datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }
 
 
# ─── Scraper ──────────────────────────────────────────────────────
 
def get_driver():
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")
    options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )
    return webdriver.Chrome(
        service=Service(ChromeDriverManager().install()),
        options=options
    )
 
 
def scrape_jadarat(max_pages=5, db_path="nabdh.db"):
    conn = init_db(db_path)
    driver = get_driver()
    all_jobs = []
 
    try:
        driver.get("https://jadarat.sa/ExploreJobs?JobTab=1")
        print("انتظار تحميل الصفحة...")
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.CLASS_NAME, "card-content"))
        )
 
        for page in range(1, max_pages + 1):
            print(f"\nالصفحة {page}")
            time.sleep(3)
 
            soup = BeautifulSoup(driver.page_source, "html.parser")
            cards = soup.find_all(class_="card-content")
            print(f"  وجدنا {len(cards)} بطاقة")
 
            if not cards:
                break
 
            page_jobs = [parse_card(c) for c in cards]
            page_jobs = [j for j in page_jobs if j["title"]]
            all_jobs.extend(page_jobs)
            print(f"  استُخرجت {len(page_jobs)} وظيفة")
 
            if page_jobs:
                j = page_jobs[0]
                print(f"  مثال: {j['title']} | {j['company']} | {j['city']}")
 
            try:
                next_btn = driver.find_element(
                    By.CSS_SELECTOR,
                    "button[aria-label='Next'], .pagination-next, li.next > a"
                )
                if next_btn.is_enabled():
                    driver.execute_script("arguments[0].click();", next_btn)
                    time.sleep(3)
                else:
                    break
            except Exception:
                print("  آخر صفحة")
                break
 
    except Exception as e:
        print(f"خطأ: {e}")
    finally:
        driver.quit()
 
    if all_jobs:
        cursor = conn.cursor()
        cursor.executemany("""
            INSERT INTO jobs (title, company, city, open_positions, post_date, source, scraped_at)
            VALUES (:title, :company, :city, :open_positions, :post_date, :source, :scraped_at)
        """, all_jobs)
        conn.commit()
        print(f"\nحُفظت {cursor.rowcount} وظيفة في {db_path}")
 
    conn.close()
    return all_jobs
 
 
# ─── اختبار من page.html ──────────────────────────────────────────
 
def test_from_file(html_path="page.html"):
    with open(html_path, encoding="utf-8") as f:
        soup = BeautifulSoup(f, "html.parser")
 
    cards = soup.find_all(class_="card-content")
    print(f"وجدنا {len(cards)} بطاقة\n")
 
    for i, card in enumerate(cards[:5], 1):
        job = parse_card(card)
        print(f"── وظيفة {i} ──")
        for k, v in job.items():
            print(f"  {k:18}: {v}")
        print()
 
 
# ─── Main ─────────────────────────────────────────────────────────
 
if __name__ == "__main__":
    import sys
    if "--test" in sys.argv:
        test_from_file("page.html")
    else:
        jobs = scrape_jadarat(max_pages=20)
        print(f"\nالإجمالي: {len(jobs)} وظيفة")