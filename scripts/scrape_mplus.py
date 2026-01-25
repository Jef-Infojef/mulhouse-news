import os
import requests
import psycopg2
from bs4 import BeautifulSoup
from dotenv import load_dotenv
import time
import random

# Configuration
load_dotenv(".env.local")
DATABASE_URL = os.environ.get("DATABASE_URL")

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'
}

def get_db_connection():
    clean_url = DATABASE_URL.replace("?pgbouncer=true", "").replace("&pgbouncer=true", "")
    return psycopg2.connect(clean_url)

def fetch_mplus_content(url):
    try:
        time.sleep(random.uniform(0.5, 1.5))
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code != 200:
            print(f"   ⚠️ Status {response.status_code}")
            return None

        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Sélecteurs pour M+
        # 1. Événements (Tribe Events)
        # 2. Articles de blog (classe 'interne')
        content_div = soup.find('div', class_='interne') or \
                      soup.find('div', class_='tribe-events-single-event-description') or \
                      soup.find('div', class_='tribe-events-content') or \
                      soup.find('div', class_='entry-content')

        if content_div:
            # On récupère aussi l'extrait s'il est séparé
            extrait = soup.find('p', class_='extrait')
            text_parts = []
            if extrait:
                text_parts.append(extrait.get_text().strip())
            
            # On nettoie le contenu principal
            for garbage in content_div.select('.important, .encadre, script, style, .sharedaddy'):
                garbage.decompose()
            
            text_parts.append(content_div.get_text("\n", strip=True))
            return "\n\n".join(text_parts)
        
        return None

    except Exception as e:
        print(f"   ❌ Erreur fetch: {e}")
        return None

def main():
    print("[*] Démarrage du scraper dédié M+ (mag.mulhouse-alsace.fr)...")
    
    conn = get_db_connection()
    cur = conn.cursor()

    # Sélectionner les articles M+ sans contenu
    cur.execute("""
        SELECT id, title, link 
        FROM \"Article\" 
        WHERE link LIKE '%mag.mulhouse-alsace.fr%' 
          AND (content IS NULL OR LENGTH(content) < 100)
    """)
    articles = cur.fetchall()
    
    if not articles:
        print("Aucun article M+ à traiter.")
        return

    print(f"[*] {len(articles)} articles M+ à traiter.")

    success_count = 0
    for i, (art_id, title, link) in enumerate(articles, 1):
        print(f"[{i}/{len(articles)}] {title[:50]}...")
        
        content = fetch_mplus_content(link)
        
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
    print(f"\n[*] Terminé. {success_count} articles M+ mis à jour.")

if __name__ == "__main__":
    main()
