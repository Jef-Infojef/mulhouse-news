
import os
import psycopg2
from bs4 import BeautifulSoup
import json
import time
import random
from curl_cffi import requests
from dotenv import load_dotenv
from datetime import datetime

# Charger l'environnement
load_dotenv(".envenv")
load_dotenv(".env.local")
load_dotenv(".env")

DATABASE_URL = os.environ.get("DATABASE_URL")

def get_db_connection():
    if not DATABASE_URL:
        raise ValueError("DATABASE_URL is not set")
    clean_url = DATABASE_URL.replace("?pgbouncer=true", "").replace("&pgbouncer=true", "")
    return psycopg2.connect(clean_url)

def get_app_config(conn, key):
    try:
        with conn.cursor() as cur:
            cur.execute('SELECT value FROM "AppConfig" WHERE key = %s', (key,))
            row = cur.fetchone()
            return row[0] if row else None
    except:
        return None

def fetch_article_content(url, cookies_dict, alsace_cookies_active):
    """Récupère le contenu complet selon la source."""
    try:
        target_url = url
        # Simplifié pour le test spécifique L'Alsace
        time.sleep(random.uniform(1.0, 2.0))
        
        try:
            resp = requests.get(target_url, cookies=cookies_dict, impersonate="chrome110", timeout=30, allow_redirects=True)
        except Exception as ssl_err:
            resp = requests.get(target_url, cookies=cookies_dict, impersonate="chrome110", timeout=30, allow_redirects=True, verify=False)
        
        if resp.status_code != 200:
            return None, True, f"HTTP {resp.status_code}"

        page_text = resp.text
        is_connected = any(x in page_text for x in ["Se déconnecter", "Mon compte", "Mon profil", "suscriber", "premium", "Abonné"])
        
        soup = BeautifulSoup(page_text, 'html.parser')
        text_parts = []

        # Logique EBRA (L'Alsace)
        if "lalsace.fr" in target_url:
            if not is_connected:
                print(f"    [⛔] Contenu partiel refusé (Non connecté)")
                return None, False, "Not Connected"

            chapo = soup.find(class_='chapo') or soup.find(class_='article__chapo')
            if chapo: text_parts.append(chapo.get_text().strip())
            
            inner = soup.find(class_='innerContent')
            if inner: text_parts.append(inner.get_text(strip=True))

            for block in soup.find_all('div', class_='textComponent'):
                txt = block.get_text("\n", strip=True)
                if len(txt) > 10: text_parts.append(txt)
            
            if not text_parts or len("\n".join(text_parts)) < 100:
                for script in soup.find_all('script', type='application/ld+json'):
                    try:
                        data = json.loads(script.string.strip())
                        items = data if isinstance(data, list) else [data]
                        for item in items:
                            if item.get('@type') in ['NewsArticle'] and item.get('description'):
                                text_parts.append(item['description'].strip())
                    except: pass

        if text_parts:
            clean_parts = [p.replace('\x00', '') for p in text_parts if p]
            return "\n\n".join(dict.fromkeys(clean_parts)), True, None
        return None, True, "No content found"
    except Exception as e:
        return None, True, str(e)

def main():
    print("=== TEST REPAIR L'ALSACE (10 ARTICLES) ===")
    conn = None
    try:
        conn = get_db_connection()
        db_session = get_app_config(conn, "EBRA_SESSION")
        db_poool = get_app_config(conn, "EBRA_POOOL")
        
        cookies_dict = {}
        if db_session:
            s_val = db_session.strip().replace('"', '').replace("'", "")
            if "2=" in s_val: s_val = s_val[s_val.find("2="):
].split(";")[0]
            p_val = db_poool.strip().replace('"', '').replace("'", "") if db_poool else "9aab6ee3-fda6-43fc-a90e-29de3c73d8f7"
            if "_poool=" in p_val: p_val = p_val.split("_poool=")[1].split(";")[0]
            
            cookies_dict = {
                ".XCONNECT_SESSION": s_val,
                ".XCONNECTKeepAlive": "2=1",
                ".XCONNECT": "2=1",
                "_poool": p_val
            }
            print(f"[*] Session active (Poool: {p_val[:8]}...)")

        cur = conn.cursor()
        cur.execute("""
            SELECT id, title, link 
            FROM "Article" 
            WHERE content IS NULL 
              AND source ILIKE '%Alsace%'
            ORDER BY "publishedAt" DESC LIMIT 10
        """)
        articles = cur.fetchall()
        
        if not articles:
            print("Aucun article trouvé.")
            return

        for i, (art_id, title, link) in enumerate(articles, 1):
            print(f"[{i}/10] Traitement : {title[:50]}...")
            content, active, err = fetch_article_content(link, cookies_dict, True)
            
            if content:
                cur.execute('UPDATE "Article" SET content = %s WHERE id = %s', (content, art_id))
                conn.commit()
                print(f"    ✅ SUCCESS ({len(content)} chars)")
            else:
                print(f"    ❌ FAILED: {err}")
            
            if not active:
                print("    [!] Session perdue ou invalide.")
                break

    except Exception as e:
        print(f"❌ Erreur : {e}")
    finally:
        if conn: conn.close()

if __name__ == "__main__":
    main()
