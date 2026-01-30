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
    # Nettoyage de l'URL pour psycopg2
    clean_url = DATABASE_URL.replace("?pgbouncer=true", "").replace("&pgbouncer=true", "")
    return psycopg2.connect(clean_url)

def fetch_jds_content(url):
    try:
        time.sleep(random.uniform(0.5, 1.5))
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code != 200:
            print(f"   ⚠️ Status {response.status_code}")
            return None

        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 1. Tentative via JSON-LD (Données structurées)
        # JDS met souvent tout le détail dans un script JSON-LD
        scripts = soup.find_all('script', type='application/ld+json')
        for script in scripts:
            try:
                data = json.loads(script.string)
                # Parfois c'est une liste, parfois un objet
                if isinstance(data, list):
                    for item in data:
                        if 'description' in item:
                            return item['description'].replace('&nbsp;', ' ')
                elif isinstance(data, dict):
                    if 'description' in data:
                        return data['description'].replace('&nbsp;', ' ')
            except:
                continue

        # 2. Fallback CSS classique
        # <div class="description clearfix mt-3">
        desc_div = soup.find('div', class_='description')
        if desc_div:
            # On nettoie un peu
            return desc_div.get_text("\n", strip=True)

        return None

    except Exception as e:
        print(f"   ❌ Erreur fetch: {e}")
        return None

def main():
    print("[*] Démarrage du scraper dédié JDS.fr...")
    
    conn = get_db_connection()
    cur = conn.cursor()

    # Sélectionner les articles JDS sans contenu
    cur.execute("""
        SELECT id, title, link 
        FROM \"Article\" 
        WHERE link LIKE '%jds.fr%' 
          AND (content IS NULL OR LENGTH(content) < 100)
    """)
    articles = cur.fetchall()
    
    if not articles:
        print("Aucun article JDS à traiter.")
        return

    print(f"[*] {len(articles)} articles JDS à traiter.")

    success_count = 0
    for i, (art_id, title, link) in enumerate(articles, 1):
        print(f"[{i}/{len(articles)}] {title[:50]}...")
        
        content = fetch_jds_content(link)
        
        if content:
            # JDS met parfois du HTML (br, etc) dans son JSON, on nettoie un peu si besoin
            # Ici on stocke brut, l'app fera le rendu si nécessaire ou on clean plus tard
            try:
                cur.execute('UPDATE "Article" SET content = %s WHERE id = %s', (content, art_id))
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
    print(f"\n[*] Terminé. {success_count} articles JDS mis à jour.")

if __name__ == "__main__":
    main()
