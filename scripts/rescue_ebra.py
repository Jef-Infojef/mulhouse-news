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
    if not found: load_dotenv()

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
    target_url = url.replace("www.dna.fr", "www.lalsace.fr").replace("www.estrepublicain.fr", "www.lalsace.fr").replace("www.vosgesmatin.fr", "www.lalsace.fr")
    try:
        time.sleep(random.uniform(1.5, 3.0))
        response = session.get(target_url, timeout=15)
        if response.status_code == 404: return None, True, target_url
        
        is_still_connected = any(x in response.text for x in ["Se déconnecter", "mon compte", "mon profil", "Abonné"])
        if not is_still_connected: return None, False, target_url

        soup = BeautifulSoup(response.text, 'html.parser')
        text_parts = []
        chapo = soup.find(class_='chapo') or soup.find(class_='article__chapo')
        if chapo: text_parts.append(chapo.get_text().strip())
        content_blocks = soup.find_all('div', class_='textComponent')
        for block in content_blocks:
            txt = block.get_text("\n", strip=True)
            if len(txt) > 10: text_parts.append(txt)
        
        if not text_parts or len("\n".join(text_parts)) < 150:
            for script in soup.find_all('script', type='application/ld+json'):
                try:
                    raw_json = script.string.strip().replace('" @', '"@')
                    import json
                    data = json.loads(raw_json)
                    items = data if isinstance(data, list) else [data]
                    for item in items:
                        if item.get('@type') in ['VideoObject', 'NewsArticle'] and item.get('description'):
                            text_parts.append(item['description'].strip())
                except: pass

        if text_parts:
            return "\n\n".join(dict.fromkeys(text_parts)), True, target_url
        return None, True, target_url
    except Exception:
        return None, True, target_url

def main():
    print("[*] Rescue EBRA v2 (Furtif) : Conversion DNA/EstRep -> L'Alsace")
    session = requests.Session()
    session.headers.update(headers)
    for key, value in cookies.items():
        session.cookies.set(key, value, domain=".lalsace.fr")

    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT id, title, link, source 
        FROM \"Article\" 
        WHERE (link LIKE '%dna.fr%' OR link LIKE '%estrepublicain.fr%' OR link LIKE '%vosgesmatin.fr%')
          AND (content IS NULL OR length(content) < 150)
        ORDER BY \"publishedAt\" DESC
    """)
    articles = cur.fetchall()
    
    if not articles:
        print("Aucun article EBRA incomplet (2025+) trouvé.")
        return

    print(f"[*] {len(articles)} articles à convertir...")
    success = 0
    deleted = 0
    
    for i, (art_id, title, link, source) in enumerate(articles, 1):
        print(f"[{i}/{len(articles)}] {title[:50]}...")
        
        # Tentative avec gestion de reconnexion DB
        try:
            content, session_active, new_link = fetch_article_content(session, link)
        except Exception as e:
            print(f"   ❌ Erreur fetch réseau: {e}")
            continue

        # On fait une pause plus longue pour simuler un humain (1.5 à 3 secondes)
        time.sleep(random.uniform(1.5, 3.0))
        
        if not session_active:
            print(f"   ⚠️ Session perdue. Attente 15s...")
            time.sleep(15)
            continue
            
        if content and len(content) > 150:
            try:
                # Vérifier si la connexion DB est toujours vivante
                if conn.closed:
                    print("[*] Reconnexion à la base de données...")
                    conn = get_db_connection()
                    cur = conn.cursor()

                cur.execute('SELECT id FROM "Article" WHERE link = %s', (new_link,))
                existing = cur.fetchone()
                
                if existing:
                    cur.execute('DELETE FROM "Article" WHERE id = %s', (art_id,))
                    deleted += 1
                    print(f"   🗑️ Doublon supprimé.")
                else:
                    cur.execute("""
                        UPDATE "Article" 
                        SET link = %s, content = %s, source = %s, "updatedAt" = NOW() 
                        WHERE id = %s
                    """, (new_link, content, "L'Alsace", art_id))
                    success += 1
                    print(f"   ✅ Converti ({len(content)} chars).")
                conn.commit()
            except (psycopg2.OperationalError, psycopg2.InterfaceError) as e:
                print(f"   ❌ Erreur DB ({e}). Reconnexion en cours...")
                conn = get_db_connection()
                cur = conn.cursor()
            except Exception as e:
                print(f"   ❌ Autre erreur DB: {e}")
                conn.rollback()
        else:
            print(f"   ⚠️ Échec.")

    cur.close()
    conn.close()
    print(f"\nTerminé : {success} convertis, {deleted} doublons supprimés.")

if __name__ == "__main__":
    main()
