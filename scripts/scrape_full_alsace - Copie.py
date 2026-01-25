import os
import requests
import psycopg2
from bs4 import BeautifulSoup
from dotenv import load_dotenv
import time
import random

# Configuration
def load_env():
    # Try multiple possible env files in the root directory (one level up from scripts/)
    root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    env_files = [".envenv", ".env.local", ".env"]
    found = False
    for f in env_files:
        path = os.path.join(root_dir, f)
        if os.path.exists(path):
            load_dotenv(path)
            # If we found DATABASE_URL, we're good
            if os.environ.get("DATABASE_URL"):
                print(f"[*] Loaded configuration from {f}")
                found = True
                break
    
    if not found:
        # Fallback to current behavior if nothing found in root
        load_dotenv(".env.local")
        load_dotenv(".env")

load_env()
DATABASE_URL = os.environ.get("DATABASE_URL")

# Le cookie fourni par l'utilisateur
COOKIES_RAW = ".XCONNECT_SESSION=2=42F647DB9B788CF4E0AFFF1DD52DE98DC84675F96D208B169CDB50252853924952A2E053A624DC98B1A3CDA071D22F3DA31D8F681B19E42BCE9E5706EF451528D1A3EFF036046BBA535A96422993FCD7544E7BD580DD2F2F64F4EF7ED699D9889ABF5CC65D13D9DB659E63A73EC4E67DA864339DA78E24CA976C5BDABEB07C17DC58F0B35E363115AD611D14315647CEB79A3171F3CEAE1E6A5944AF8887007015CCF79D15E8D78DA28D91E9364047E7BC79E91E8390DB6AEC6C5E42F8E3B55F978CC890F21BC2D73AD4F761E7AE7161EFBA5686005A0123FE60996E1065716E5BF06D41F7AC; domain=lalsace.fr; expires=Thu, 09-Jul-2026 18:00:39 GMT; path=/; secure; HttpOnly; SameSite=Lax"

# Parsing du cookie brut pour requests
cookies = {}
for part in COOKIES_RAW.split(';'):
    if '=' in part:
        key, value = part.strip().split('=', 1)
        cookies[key] = value

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
}

def get_db_connection():
    return psycopg2.connect(DATABASE_URL)

def clean_text(text):
    if not text: return None
    return text.strip()

def fetch_article_content(url):
    try:
        time.sleep(random.uniform(0.5, 1.5)) # Pause polie
        response = requests.get(url, headers=headers, cookies=cookies, timeout=15)
        
        if response.status_code != 200:
            print(f"   ⚠️ Status {response.status_code}")
            return None

        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Détection Paywall
        if soup.find(class_='paywall') or soup.find(class_='paywall1') or soup.find(id='paywall'):
            print("   ⚠️ Paywall détecté (cookie invalide ou expiré ?)")

        # Sélecteurs potentiels pour le contenu principal
        text_parts = []
        
        # 1. Le titre (pour le contexte, optionnel mais utile)
        # title = soup.find('h1')
        # if title: text_parts.append(title.get_text().strip())

        # 2. Le Chapô (souvent présent même si paywall)
        chapo = soup.find(class_='chapo') or soup.find(class_='article__chapo')
        if chapo:
            text_parts.append(chapo.get_text().strip())

        # 3. Le corps de l'article (plusieurs variantes possibles)
        content_div = soup.find('div', class_='c-article-content') or \
                      soup.find('div', itemprop='articleBody') or \
                      soup.find('div', class_='int-article-content') or \
                      soup.find('div', class_='textComponent') or \
                      soup.find(class_='article__body')

        if content_div:
            # Suppression des éléments indésirables
            for garbage in content_div.select('.c-read-also, .gl-ad, script, style, .dfp-ad-slot, .article__aside, .related-articles'):
                garbage.decompose()
            
            # Récupération du texte
            paragraphs = [p.get_text().strip() for p in content_div.find_all('p') if p.get_text().strip()]
            text_parts.extend(paragraphs)

        if text_parts:
            full_text = "\n\n".join(text_parts)
            return full_text
        else:
            print("   ⚠️ Aucun contenu trouvé (ni chapô ni corps)")
            return None

    except Exception as e:
        print(f"   ❌ Erreur fetch: {e}")
        return None

def main():
    print("[*] Démarrage du scraping complet L'Alsace...")
    
    conn = get_db_connection()
    cur = conn.cursor()

    # On commence par les articles les plus récents sans contenu
    cur.execute("""
        SELECT id, title, link, source 
        FROM \"Article\" 
        WHERE source ILIKE '%Alsace%' 
          AND content IS NULL
        ORDER BY \"publishedAt\" DESC
        LIMIT 50
    """)
    articles = cur.fetchall()
    
    if not articles:
        print("Aucun article à traiter.")
        return

    print(f"[*] Traitement de {len(articles)} articles pour test...")

    success_count = 0
    for i, (art_id, title, link, source) in enumerate(articles, 1):
        print(f"[{i}/{len(articles)}] {title[:50]}...")
        
        content = fetch_article_content(link)
        
        if content and len(content) > 100:
            try:
                cur.execute('UPDATE "Article" SET content = %s WHERE id = %s', (content, art_id))
                conn.commit()
                print(f"   ✅ Contenu récupéré ({len(content)} chars)")
                success_count += 1
            except Exception as e:
                print(f"   ❌ Erreur BDD: {e}")
                conn.rollback()
        else:
            print("   ⚠️ Contenu vide ou trop court")

    cur.close()
    conn.close()
    print(f"\n[*] Terminé. {success_count} articles mis à jour.")

if __name__ == "__main__":
    main()
