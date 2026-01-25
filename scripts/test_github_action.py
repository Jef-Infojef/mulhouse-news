import os
import requests
import psycopg2
from bs4 import BeautifulSoup
import json

def load_config():
    db_url = os.environ.get("DATABASE_URL")
    cookies_raw = os.environ.get("ALSACE_COOKIES")
    
    if cookies_raw:
        print(f"[*] Secret ALSACE_COOKIES détecté (longueur: {len(cookies_raw)})")
    else:
        print("❌ Secret ALSACE_COOKIES NON DÉTECTÉ dans l'environnement")
        
    return db_url, cookies_raw

def fetch_content(session, url):
    print(f"[*] Fetching: {url}")
    try:
        resp = session.get(url, timeout=20)
        page_text = resp.text.lower()
        
        # Marqueurs de connexion
        is_connected = any(x in page_text for x in ["se déconnecter", "mon compte", "premium", "suscriber"])
        print(f"[*] État session : {'✅ CONNECTÉ' if is_connected else '❌ NON CONNECTÉ'}")
        
        soup = BeautifulSoup(resp.text, 'html.parser')
        text_parts = []
        
        # Chapô
        chapo = soup.find(class_='chapo') or soup.find(class_='article__chapo')
        if chapo: text_parts.append(chapo.get_text().strip())
        
        # Corps
        content_blocks = soup.find_all('div', class_='textComponent')
        for block in content_blocks:
            txt = block.get_text("\n", strip=True)
            if len(txt) > 10: text_parts.append(txt)
            
        # LD+JSON
        if not text_parts or len("\n".join(text_parts)) < 300:
            for script in soup.find_all('script', type='application/ld+json'):
                try:
                    data = json.loads(script.string)
                    items = data if isinstance(data, list) else [data]
                    for item in items:
                        if item.get('@type') in ['VideoObject', 'NewsArticle'] and item.get('description'):
                            desc = item['description'].strip()
                            if len(desc) > 100: text_parts.append(desc)
                except: pass

        return "\n\n".join(text_parts)
    except Exception as e:
        print(f"❌ Erreur fetch : {e}")
        return None

def main():
    print("=== TEST SCRAPER GITHUB ACTIONS V6 ===")
    db_url, cookies_raw = load_config()
    if not db_url: return

    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
    })
    
    if cookies_raw:
        # Nettoyage simple
        raw = cookies_raw.strip().replace('"', '').replace("'", "")
        # On injecte la chaîne brute dans le header Cookie (plus fiable que session.cookies)
        session.headers['Cookie'] = raw
        print("[*] Cookies injectés dans les headers.")

    try:
        url = db_url.replace("?pgbouncer=true", "")
        conn = psycopg2.connect(url)
        cur = conn.cursor()
        cur.execute("""
            SELECT title, link FROM \"Article\" 
            WHERE source ILIKE '%Alsace%' AND link LIKE '%www.lalsace.fr%' AND content IS NULL 
            ORDER BY \"publishedAt\" DESC LIMIT 1
        """)
        article = cur.fetchone()
        if article:
            print(f"[*] Article : {article[0]}")
            content = fetch_content(session, article[1])
            if content:
                print(f"✅ RÉSULTAT : {len(content)} caractères.")
                print(content[:500] + "...")
            else:
                print("❌ RÉSULTAT : Vide.")
        cur.close()
        conn.close()
    except Exception as e:
        print(f"❌ Erreur BDD : {e}")

if __name__ == "__main__":
    main()