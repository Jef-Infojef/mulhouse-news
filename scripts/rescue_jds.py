import os
import psycopg2
import time
import random
from curl_cffi import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv

load_dotenv(".env")
DATABASE_URL = os.environ.get("DATABASE_URL")

def get_db_connection():
    clean_url = DATABASE_URL.replace("?pgbouncer=true", "").replace("&pgbouncer=true", "")
    return psycopg2.connect(clean_url)

def fetch_jds_content(url):
    try:
        time.sleep(random.uniform(0.5, 1.2))
        resp = requests.get(url, impersonate="chrome110", timeout=20)
        if resp.status_code != 200: return None
        
        soup = BeautifulSoup(resp.text, 'html.parser')
        desc_div = soup.find('div', class_='description') or soup.find('div', id='description') or soup.find('div', itemprop='description')
        
        if desc_div:
            return desc_div.get_text(separator="\n", strip=True)
        return None
    except: return None

def main():
    print("=== RATTRAPAGE JDS.FR (JANVIER 2026) ===")
    conn = get_db_connection()
    cur = conn.cursor()

    # On cible tous les articles JDS sans contenu
    cur.execute("""
        SELECT id, title, link 
        FROM \"Article\" 
        WHERE source ILIKE '%jds%' 
          AND (content IS NULL OR content = '')
          AND \"publishedAt\" >= '2026-01-01'
    """)
    events = cur.fetchall()
    print(f"[*] {len(events)} evenements JDS identifiés.")

    success = 0
    for i, (art_id, title, link) in enumerate(events, 1):
        print(f"[{i}/{len(events)}] Extraction: {title[:50]}...", end=" ", flush=True)
        content = fetch_jds_content(link)
        
        if content:
            cur.execute('UPDATE \"Article\" SET content = %s WHERE id = %s', (content, art_id))
            conn.commit()
            print(f"✅ ({len(content)} chars)")
            success += 1
        else:
            print("❌")

    print(f"\n[*] TERMINÉ. {success} événements JDS complétés.")
    cur.close()
    conn.close()

if __name__ == "__main__":
    main()
