import os
import requests
import psycopg2
from bs4 import BeautifulSoup
import json

def load_config():
    db_url = os.environ.get("DATABASE_URL")
    cookies_raw = os.environ.get("ALSACE_COOKIES")
    return db_url, cookies_raw

def fetch_content(session, url):
    print(f"[*] Fetching: {url}")
    try:
        resp = session.get(url, timeout=20)
        
        # Vérification de connexion améliorée
        page_text = resp.text.lower()
        # On cherche des indices de profil abonné
        is_connected = any(x in page_text for x in ["se déconnecter", "mon compte", "mon profil", "suscriber", "premium"])
        
        print(f"[*] État session sur GitHub : {'✅ CONNECTÉ' if is_connected else '❌ NON CONNECTÉ'}")
        
        soup = BeautifulSoup(resp.text, 'html.parser')
        text_parts = []
        
        # 1. Chapô
        chapo = soup.find(class_='chapo') or soup.find(class_='article__chapo')
        if chapo: text_parts.append(chapo.get_text().strip())
        
        # 2. Corps (textComponent)
        content_blocks = soup.find_all('div', class_='textComponent')
        for block in content_blocks:
            txt = block.get_text("\n", strip=True)
            if len(txt) > 10: text_parts.append(txt)
            
        # 3. Fallback Vidéo/LD+JSON
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
    print("=== TEST SCRAPER GITHUB ACTIONS V5 ===")
    db_url, cookies_raw = load_config()
    if not db_url: return

    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
        'Accept-Language': 'fr-FR,fr;q=0.9',
    })
    
    if cookies_raw:
        # Nettoyage et affectation intelligente
        raw = cookies_raw.replace('"', '').replace("'", "").strip()
        
        # Cas spécial : l'utilisateur n'a mis que la valeur "2=42F6..."
        if raw.startswith('2=') and '.XCONNECT_SESSION' not in raw:
            session.cookies.set(".XCONNECT_SESSION", raw, domain=".lalsace.fr")
            print("[*] Cookie .XCONNECT_SESSION configuré automatiquement.")
        
        # Traitement des autres cookies (séparés par ;)
        parts = [p.strip() for p in raw.split(';') if '=' in p]
        for p in parts:
            k, v = p.split('=', 1)
            k = k.strip()
            if k == ".XCONNECT_SESSION":
                session.cookies.set(k, v.strip(), domain=".lalsace.fr")
            elif k in [".XCONNECTKeepAlive", ".XCONNECT", "_poool"]:
                session.cookies.set(k, v.strip(), domain=".lalsace.fr")
        
        print(f"[*] Cookies chargés : {', '.join(session.cookies.get_dict().keys())}")

    try:
        url = db_url.replace("?pgbouncer=true", "")
        conn = psycopg2.connect(url)
        cur = conn.cursor()
        # On cherche un article récent sans contenu
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
                print(f"✅ SUCCÈS : {len(content)} caractères.")
                print(content[:500] + "...")
            else:
                print("❌ ÉCHEC : Contenu vide.")
        cur.close()
        conn.close()
    except Exception as e:
        print(f"❌ Erreur BDD : {e}")

if __name__ == "__main__":
    main()
