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
    found = False
    for f in env_files:
        path = os.path.join(root_dir, f)
        if os.path.exists(path):
            load_dotenv(path)
            if os.environ.get("DATABASE_URL"):
                print(f"[*] Configuration chargée depuis {f}")
                found = True
                break
    if not found:
        load_dotenv()

load_env()
DATABASE_URL = os.environ.get("DATABASE_URL")

# Cookie session fourni le 25/01/2026
COOKIES_RAW = ".XCONNECT_SESSION=2=42F647DB9B788CF4E0AFFF1DD52DE98D13D5BEAE4D0A7548CB51419BA062EAE71D99523ACD1B12EFA647F09355124D3C9B80D02280FCB30CDBBFB57D159E1343BA829705D2D36D99EF603631BE2DE11A9DC7946BAE377A21B69489F56207EB0AD9015AEBE1EF36616DB621DE6B0B335E8C9044C3C9975C3BB6750CC6E382D1922EFD7DAA2D846F75F761E4F4E5370352C6110B8C46AED633FA44DA2B35DFDE0D09F83B8CAF574CFC09B7E9788678AB700BC89DA804B559BE1FE9CFAE44775CC7BE6370D829B6A402D0945181A2FCD0B322A9411AFBC0DA047DE7F55EEB7379F7C92D46905E86A58E8EB557C8994B153B; .XCONNECTKeepAlive=2=1; .XCONNECT=2=1; _poool=9aab6ee3-fda6-43fc-a90e-29de3c73d8f7; domain=lalsace.fr; path=/; secure; HttpOnly; SameSite=Lax"

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
        time.sleep(random.uniform(0.6, 1.2))
        response = session.get(url, timeout=15)
        if response.status_code != 200: return None, True
        
        is_still_connected = any(x in response.text for x in ["Se déconnecter", "mon compte", "mon profil"])
        is_special_page = any(x in url.lower() for x in ["video", "diaporama", "grand-format"])
        
        if not is_still_connected and not is_special_page:
            return None, False

        soup = BeautifulSoup(response.text, 'html.parser')
        text_parts = []
        
        chapo = soup.find(class_='chapo') or soup.find(class_='article__chapo')
        if chapo: text_parts.append(chapo.get_text().strip())

        content_blocks = soup.find_all('div', class_='textComponent')
        for block in content_blocks:
            txt = block.get_text("\n", strip=True)
            if len(txt) > 10: text_parts.append(txt)
        
        if not text_parts:
            # Fallback JSON-LD
            import json
            for script in soup.find_all('script', type='application/ld+json'):
                try:
                    raw_json = script.string.strip().replace('" @', '"@')
                    data = json.loads(raw_json)
                    items = data if isinstance(data, list) else [data]
                    for item in items:
                        if item.get('@type') in ['VideoObject', 'NewsArticle'] and item.get('description'):
                            text_parts.append(item['description'].strip())
                except: pass

        if text_parts:
            full_text = "\n\n".join(dict.fromkeys(text_parts))
            return full_text, True
        return None, True
    except Exception:
        return None, True

def check_connection(session):
    print("[*] Vérification de la connexion...")
    try:
        response = session.get("https://www.lalsace.fr/", timeout=15)
        if "Se déconnecter" in response.text or "mon compte" in response.text.lower():
            print("   ✅ Connecté avec succès !")
            return True
        print("   ❌ Non connecté (cookie invalide)")
        return False
    except Exception:
        return False

def main():
    print("[*] Démarrage du scraping L'Alsace (Archives 2009-2020)...")
    session = requests.Session()
    session.headers.update(headers)
    for key, value in cookies.items():
        session.cookies.set(key, value, domain=".lalsace.fr")

    is_connected = check_connection(session)
    if not is_connected:
        print("   ⚠️ Mode sans connexion (limité aux articles gratuits)")
        confirm = input("[?] Continuer quand même ? (y/n) : ")
        if confirm.lower() != 'y': return

    conn = get_db_connection()
    cur = conn.cursor()

    # Archives lalsace.fr uniquement
    cur.execute("""
        SELECT id, title, link, "publishedAt"
        FROM \"Article\" 
        WHERE link LIKE '%lalsace.fr%'
          AND content IS NULL
          AND "publishedAt" >= '2009-01-01'
          AND "publishedAt" <= '2020-12-31'
        ORDER BY "publishedAt" DESC
    """)
    articles = cur.fetchall()
    
    if not articles:
        print("Aucun article archive sans contenu trouvé.")
        return

    print(f"[*] Traitement de {len(articles)} articles archives...")
    stats = {"success": 0, "fail": 0, "session_lost": False}
    
    for i, (art_id, title, link, pub_date) in enumerate(articles, 1):
        content, session_active = fetch_article_content(session, link)
        if not session_active:
            print(f"\n[!] ARRÊT CRITIQUE : Session perdue à l'article {i}.")
            stats["session_lost"] = True
            break
        
        if content and len(content) > 150:
            try:
                cur.execute('UPDATE "Article" SET content = %s WHERE id = %s', (content, art_id))
                conn.commit()
                print(f"[{i}/{len(articles)}] ✅ {pub_date.year} | {len(content)} chars | {title[:40]}...")
                stats["success"] += 1
            except Exception as e:
                conn.rollback()
                print(f"[{i}/{len(articles)}] ❌ Erreur BDD: {e}")
                stats["fail"] += 1
        else:
            print(f"[{i}/{len(articles)}] ⚠️ {pub_date.year} | Échec/Court | {title[:40]}...")
            stats["fail"] += 1

    cur.close()
    conn.close()
    print(f"\nTerminé : {stats['success']} articles récupérés.")

if __name__ == "__main__":
    main()