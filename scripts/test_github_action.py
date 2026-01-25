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
        
        # Debug Cookies envoyés
        sent_cookies = session.cookies.get_dict()
        print(f"[*] Cookies envoyés ({len(sent_cookies)}) : {', '.join(sent_cookies.keys())}")

        # Détection de la connexion
        page_text = resp.text.lower()
        is_connected = "se déconnecter" in page_text or "mon compte" in page_text or "connected" in page_text
        print(f"[*] État session : {'✅ CONNECTÉ' if is_connected else '❌ NON CONNECTÉ'}")
        
        print("[!] Extrait du corps HTML (début) :")
        soup = BeautifulSoup(resp.text, 'html.parser')
        body_text = soup.get_text(" ", strip=True)
        print(body_text[:1000] + "...")

        text_parts = []
        # 1. Chapô
        chapo = soup.find(class_='chapo') or soup.find(class_='article__chapo')
        if chapo: 
            print("   ✅ Chapô trouvé")
            text_parts.append(chapo.get_text().strip())
        
        # 2. Corps (textComponent)
        content_blocks = soup.find_all('div', class_='textComponent')
        if content_blocks:
            print(f"   ✅ {len(content_blocks)} blocs textComponent trouvés")
            for block in content_blocks:
                txt = block.get_text("\n", strip=True)
                if len(txt) > 10: text_parts.append(txt)
            
        # 3. Vidéo (LD+JSON)
        scripts = soup.find_all('script', type='application/ld+json')
        print(f"   🔍 Blocs LD+JSON trouvés : {len(scripts)}")
        for script in scripts:
            try:
                data = json.loads(script.string)
                items = data if isinstance(data, list) else [data]
                for item in items:
                    if item.get('@type') in ['VideoObject', 'NewsArticle'] and item.get('description'):
                        desc = item['description'].strip()
                        if len(desc) > 100:
                            print(f"   ✅ Description trouvée dans LD+JSON ({item.get('@type')})")
                            text_parts.append(desc)
            except: pass

        return "\n\n".join(text_parts)
    except Exception as e:
        print(f"❌ Erreur fetch : {e}")
        return None

def main():
    print("=== TEST SCRAPER GITHUB ACTIONS V3 ===")
    db_url, cookies_raw = load_config()
    if not db_url: 
        print("❌ DATABASE_URL manquante")
        return

    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
        'Accept-Language': 'fr-FR,fr;q=0.9',
    })
    
    if cookies_raw:
        print("[*] Chargement des cookies depuis le secret...")
        parts = [p.strip() for p in cookies_raw.split(';') if '=' in p]
        for p in parts:
            k, v = p.split('=', 1)
            session.cookies.set(k, v, domain=".lalsace.fr")
    else:
        print("⚠️ ALSACE_COOKIES manquante dans les secrets")

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
                print(f"✅ RÉSULTAT : {len(content)} chars.")
                print(content[:500] + "...")
            else:
                print("❌ RÉSULTAT : Vide.")
        cur.close()
        conn.close()
    except Exception as e:
        print(f"❌ Erreur BDD : {e}")

if __name__ == "__main__":
    main()
