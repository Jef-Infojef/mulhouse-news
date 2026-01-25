import os
import requests
import psycopg2
from bs4 import BeautifulSoup
from dotenv import load_dotenv
import time
import random

# Configuration
def load_env():
    root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    env_files = [".envenv", ".env.local", ".env"]
    for f in env_files:
        path = os.path.join(root_dir, f)
        if os.path.exists(path):
            load_dotenv(path)
            if os.environ.get("DATABASE_URL"):
                break
    load_dotenv()

load_env()
DATABASE_URL = os.environ.get("DATABASE_URL")

# Cookie session (extrait du script 2022)
COOKIES_RAW = ".XCONNECT_SESSION=2=42F647DB9B788CF4E0AFFF1DD52DE98DE5A450077C33F5DBE48EB317AE414F79D3DAD2E7DB6DEB3C0134EC2B90AA723CBDD640EE3B4DB101F66141756680897908EE44059F958A00B10BEC640D2A6B3CD013743A0F8EB559408BBB8A40CDC08A322B3FCF12FCB8E9F0FB3F3A120D8465E608A45E735A955CD5194F5522DA617B94ECDF160434AD3494C70BFE3A7E85AD129AF09DED774176A79FD3B61B59691800091CB0DCC07FF8879783D0F3AE452F7439D934068B37B49DAE0811B65AAA2F6BE959F599DCDE38FDB5EF0431CE5C23E9D301E18932EE38A8FED14961A455EFC10A3E23981819A89284433B50473DD0; .XCONNECTKeepAlive=2=1; .XCONNECT=2=1; _poool=9aab6ee3-fda6-43fc-a90e-29de3c73d8f7; domain=lalsace.fr; path=/; secure; HttpOnly; SameSite=Lax"

cookies = {}
for part in COOKIES_RAW.split(';'):
    if '=' in part:
        key, value = part.strip().split('=', 1)
        cookies[key] = value

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
    'Accept-Language': 'fr-FR,fr;q=0.9',
}

def get_db_connection():
    url = DATABASE_URL
    if url and "DATABASE_URL=\"" in url:
        url = url.replace("DATABASE_URL=\"", "").replace("\"", "")
    if url and "?pgbouncer=true" in url:
        url = url.replace("?pgbouncer=true", "")
    return psycopg2.connect(url)

def fetch_article_content(session, url):
    try:
        time.sleep(random.uniform(0.5, 1.2))
        response = session.get(url, timeout=15)
        if response.status_code != 200: return None, True
        
        is_still_connected = "Se déconnecter" in response.text or "mon compte" in response.text.lower()
        if not is_still_connected: return None, False

        soup = BeautifulSoup(response.text, 'html.parser')
        text_parts = []
        
        chapo = soup.find(class_='chapo') or soup.find(class_='article__chapo')
        if chapo: text_parts.append(chapo.get_text().strip())

        content_blocks = soup.find_all('div', class_='textComponent')
        if content_blocks:
            for block in content_blocks:
                block_text = block.get_text("\n", strip=True)
                if len(block_text) > 10: text_parts.append(block_text)
        
        if not text_parts:
            content_div = soup.find('div', class_='c-article-content') or soup.find('div', itemprop='articleBody')
            if content_div:
                paragraphs = [p.get_text().strip() for p in content_div.find_all(['p', 'h2']) if p.get_text().strip()]
                text_parts.extend(paragraphs)

        return ("\n\n".join(text_parts), True) if text_parts else (None, True)
    except Exception:
        return None, True

def main():
    print("[*] Scraping L'Alsace : Archives 2009 -> 2020")
    session = requests.Session()
    session.headers.update(headers)
    for key, value in cookies.items():
        session.cookies.set(key, value, domain=".lalsace.fr")

    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT id, title, link, "publishedAt"
        FROM "Article" 
        WHERE (source ILIKE '%Alsace%' OR link LIKE '%lalsace.fr%')
          AND content IS NULL
          AND "publishedAt" >= '2009-01-01'
          AND "publishedAt" <= '2020-12-31'
        ORDER BY "publishedAt" DESC
    """)
    articles = cur.fetchall()
    
    if not articles:
        print("Aucun article trouvé pour cette période.")
        return

    print(f"[*] {len(articles)} articles à traiter.")
    
    success = 0
    for i, (art_id, title, link, pub_date) in enumerate(articles, 1):
        content, session_active = fetch_article_content(session, link)
        
        if not session_active:
            print(f"\n[!] Session perdue. Arrêt.")
            break
            
        if content and len(content) > 150:
            cur.execute('UPDATE "Article" SET content = %s WHERE id = %s', (content, art_id))
            conn.commit()
            print(f"[{i}/{len(articles)}] ✅ {pub_date.year} | {len(content)} chars | {title[:40]}...")
            success += 1
        else:
            print(f"[{i}/{len(articles)}] ⚠️ {pub_date.year} | Échec/Court | {title[:40]}...")

    cur.close()
    conn.close()
    print(f"\nTerminé : {success} articles récupérés.")

if __name__ == "__main__":
    main()
