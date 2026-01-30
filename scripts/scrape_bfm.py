import os
import requests
import psycopg2
import json
from bs4 import BeautifulSoup
from dotenv import load_dotenv
import time
import random

# Configuration
load_dotenv(".env.local")
DATABASE_URL = os.environ.get("DATABASE_URL")

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
}

def get_db_connection():
    clean_url = DATABASE_URL.replace("?pgbouncer=true", "").replace("&pgbouncer=true", "")
    return psycopg2.connect(clean_url)

def fetch_bfm_content(url):
    try:
        time.sleep(random.uniform(0.5, 1.5))
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code != 200:
            print(f"   ⚠️ Status {response.status_code}")
            return None

        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 1. Tentative via JSON-LD (Données structurées)
        scripts = soup.find_all('script', type='application/ld+json')
        for script in scripts:
            try:
                data = json.loads(script.string)
                # Parfois c'est une liste, parfois un objet
                if isinstance(data, list):
                    for item in data:
                        if 'description' in item:
                            return item['description']
                elif isinstance(data, dict):
                    if 'description' in data:
                        return data['description']
            except:
                continue

        # 2. Fallback CSS
        desc_span = soup.find('span', class_='content_description_text') or \
                    soup.find('div', class_='content_description')
        if desc_span:
            return desc_span.get_text().strip()

        return None

    except Exception as e:
        print(f"   ❌ Erreur fetch: {e}")
        return None

def main():
    print("[*] Démarrage du scraper dédié BFM...")
    
    conn = get_db_connection()
    cur = conn.cursor()

    # Sélectionner les articles BFM sans contenu
    cur.execute("""
        SELECT id, title, link 
        FROM \"Article\" 
        WHERE (link LIKE '%bfmtv.com%' OR source LIKE '%BFM%')
          AND (content IS NULL OR LENGTH(content) < 100)
    """)
    articles = cur.fetchall()
    
    if not articles:
        print("Aucun article BFM à traiter.")
        return

    print(f"[*] {len(articles)} articles BFM à traiter.")

    success_count = 0
    for i, (art_id, title, link) in enumerate(articles, 1):
        print(f"[{i}/{len(articles)}] {title[:50]}...")
        
        content = fetch_bfm_content(link)
        
        if content:
            try:
                cur.execute('UPDATE \"Article\" SET content = %s WHERE id = %s', (content, art_id))
                conn.commit()
                print(f"   ✅ Contenu récupéré ({len(content)} chars)")
                success_count += 1
            except Exception as e:
                print(f"   ❌ Erreur BDD: {e}")
                conn.rollback()
        else:
            print("   ⚠️ Contenu non trouvé")

    cur.close()
    conn.close()
    print(f"\n[*] Terminé. {success_count} articles BFM mis à jour.")

if __name__ == "__main__":
    main()
