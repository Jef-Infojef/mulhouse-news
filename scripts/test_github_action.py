import os
import requests
import psycopg2
from bs4 import BeautifulSoup
import json

# URL pour configurer les secrets : https://github.com/Jef-Infojef/mulhouse-news/settings/secrets/actions

def load_config():
    db_url = os.environ.get("DATABASE_URL")
    cookies_raw = os.environ.get("ALSACE_COOKIES")
    return db_url, cookies_raw

def fetch_content(session, url):
    print(f"[*] Fetching: {url}")
    try:
        resp = session.get(url, timeout=20)
        
        # Détection de la connexion
        page_text = resp.text.lower()
        is_connected = "se déconnecter" in page_text or "mon compte" in page_text
        print(f"[*] État session : {'✅ CONNECTÉ' if is_connected else '❌ NON CONNECTÉ'}")
        
        if not is_connected:
            print("[!] Extrait du HTML (500 premiers chars) pour debug :")
            print(resp.text[:500].replace('\n', ' '))

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
            
        # 3. Vidéo (LD+JSON)
        if not text_parts or len("\n".join(text_parts)) < 200:
            for script in soup.find_all('script', type='application/ld+json'):
                try:
                    data = json.loads(script.string)
                    items = data if isinstance(data, list) else [data]
                    for item in items:
                        if item.get('@type') in ['VideoObject', 'NewsArticle'] and item.get('description'):
                            # On ne prend la description que si elle est longue (pour éviter les doublons de chapô)
                            desc = item['description'].strip()
                            if len(desc) > 100:
                                text_parts.append(desc)
                except: pass

        return "\n\n".join(text_parts)
    except Exception as e:
        print(f"❌ Erreur fetch : {e}")
        return None

def main():
    print("=== TEST SCRAPER GITHUB ACTIONS V2 ===")
    db_url, cookies_raw = load_config()
    if not db_url: return

    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
        'Accept-Language': 'fr-FR,fr;q=0.9',
    })
    
    if cookies_raw:
        # On nettoie et on applique les cookies sur tous les domaines possibles
        parts = [p.strip() for p in cookies_raw.split(';') if '=' in p]
        for p in parts:
            k, v = p.split('=', 1)
            session.cookies.set(k, v, domain=".lalsace.fr")
            session.cookies.set(k, v, domain="www.lalsace.fr")

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
            title, link = article
            print(f"[*] Article de test : {title}")
            content = fetch_content(session, link)
            
            if content:
                print(f"✅ SUCCÈS : {len(content)} caractères récupérés.")
                print("-" * 30)
                print(content[:1000] + ("..." if len(content) > 1000 else ""))
                print("-" * 30)
            else:
                print("❌ ÉCHEC : Aucun contenu.")
        else:
            print("ℹ️ Aucun article à tester.")
            
        cur.close()
        conn.close()
    except Exception as e:
        print(f"❌ Erreur BDD : {e}")

if __name__ == "__main__":
    main()