import os
import requests
import psycopg2
from bs4 import BeautifulSoup
import json

# URL pour configurer les secrets : https://github.com/Jef-Infojef/mulhouse-news/settings/secrets/actions
# Secrets à ajouter :
# 1. DATABASE_URL
# 2. ALSACE_COOKIES (la valeur complète de COOKIES_RAW)

def load_config():
    # Sur GitHub, les secrets sont injectés dans l'environnement
    db_url = os.environ.get("DATABASE_URL")
    cookies_raw = os.environ.get("ALSACE_COOKIES")
    
    if not db_url:
        print("❌ ERREUR : DATABASE_URL non trouvée dans l'environnement.")
    if not cookies_raw:
        print("⚠️ WARNING : ALSACE_COOKIES non trouvée. Test en mode non-connecté.")
        
    return db_url, cookies_raw

def fetch_content(session, url):
    print(f"[*] Fetching: {url}")
    try:
        resp = session.get(url, timeout=20)
        print(f"[*] Status Code: {resp.status_code}")
        
        if resp.status_code == 403:
            print("❌ ACCÈS REFUSÉ (403) : GitHub est probablement bloqué par L'Alsace.")
            return None
            
        is_connected = "Se déconnecter" in resp.text or "mon compte" in resp.text.lower()
        print(f"[*] État session sur la page : {'✅ CONNECTÉ' if is_connected else '❌ NON CONNECTÉ'}")
        
        soup = BeautifulSoup(resp.text, 'html.parser')
        text_parts = []
        
        # Logique d'extraction identique à notre scraper local
        chapo = soup.find(class_='chapo') or soup.find(class_='article__chapo')
        if chapo: text_parts.append(chapo.get_text().strip())
        
        content_blocks = soup.find_all('div', class_='textComponent')
        for block in content_blocks:
            txt = block.get_text("\n", strip=True)
            if len(txt) > 10: text_parts.append(txt)
            
        if not text_parts:
            # Fallback Vidéo
            for script in soup.find_all('script', type='application/ld+json'):
                try:
                    data = json.loads(script.string)
                    items = data if isinstance(data, list) else [data]
                    for item in items:
                        if item.get('@type') == 'VideoObject' and item.get('description'):
                            text_parts.append(item['description'])
                except: pass

        return "\n\n".join(text_parts)
    except Exception as e:
        print(f"❌ Erreur réseau : {e}")
        return None

def main():
    print("=== TEST SCRAPER GITHUB ACTIONS ===")
    db_url, cookies_raw = load_config()
    
    if not db_url: return

    # Setup Session
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36'
    })
    
    if cookies_raw:
        cookies = {}
        for part in cookies_raw.split(';'):
            if '=' in part:
                k, v = part.strip().split('=', 1)
                cookies[k] = v
        for k, v in cookies.items():
            session.cookies.set(k, v, domain=".lalsace.fr")

    # Connexion DB pour trouver un article de test
    try:
        url = db_url.replace("?pgbouncer=true", "")
        conn = psycopg2.connect(url)
        cur = conn.cursor()
        
        cur.execute("""
            SELECT title, link FROM \"Article\" 
            WHERE source ILIKE '%Alsace%' AND link LIKE '%lalsace.fr%' AND content IS NULL 
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
                print(content[:500] + "...")
                print("-" * 30)
            else:
                print("❌ ÉCHEC : Aucun contenu récupéré.")
        else:
            print("ℹ️ Aucun article sans contenu trouvé en base pour le test.")
            
        cur.close()
        conn.close()
    except Exception as e:
        print(f"❌ Erreur Base de données : {e}")

if __name__ == "__main__":
    main()
