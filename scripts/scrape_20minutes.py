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

def fetch_20minutes_content(url):
    try:
        time.sleep(random.uniform(0.5, 1.5))
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code != 200:
            print(f"   ⚠️ Status {response.status_code}")
            return None

        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 1. Tentative via JSON-LD (articleBody est souvent complet)
        scripts = soup.find_all('script', type='application/ld+json')
        for script in scripts:
            try:
                data = json.loads(script.string)
                if isinstance(data, dict) and data.get('@type') == 'NewsArticle' and 'articleBody' in data:
                    return data['articleBody']
            except:
                continue

        # 2. Fallback CSS
        text_parts = []
        
        # Chapô
        lead = soup.find(id='content-header-lead')
        if lead:
            text_parts.append(lead.get_text().strip())
            
        # Corps
        content_div = soup.find('div', class_='c-content')
        if content_div:
            # On nettoie les pubs et "A lire aussi"
            for garbage in content_div.select('.c-ad-placeholder, .c-read-also, script, style, figure'):
                garbage.decompose()
            
            for element in content_div.find_all(['p', 'h2']):
                txt = element.get_text().strip()
                if txt and len(txt) > 5:
                    text_parts.append(txt)

        if text_parts:
            # Unicité pour éviter les doublons chapo/corps
            unique = []
            for p in text_parts:
                if p not in unique:
                    unique.append(p)
            return "\n\n".join(unique)

        return None

    except Exception as e:
        print(f"   ❌ Erreur fetch: {e}")
        return None

def main():
    print("[*] Démarrage du scraper dédié 20 Minutes...")
    
    conn = get_db_connection()
    cur = conn.cursor()

    # Sélectionner les articles 20 Minutes sans contenu
    cur.execute("""
        SELECT id, title, link 
        FROM \"Article\" 
        WHERE (link LIKE '%20minutes.fr%' OR source LIKE '%20 Minutes%')
          AND (content IS NULL OR LENGTH(content) < 100)
    """)
    articles = cur.fetchall()
    
    if not articles:
        print("Aucun article 20 Minutes à traiter.")
        return

    print(f"[*] {len(articles)} articles 20 Minutes à traiter.")

    success_count = 0
    for i, (art_id, title, link) in enumerate(articles, 1):
        print(f"[{i}/{len(articles)}] {title[:50]}...")
        
        content = fetch_20minutes_content(link)
        
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
    print(f"\n[*] Terminé. {success_count} articles 20 Minutes mis à jour.")

if __name__ == "__main__":
    main()
