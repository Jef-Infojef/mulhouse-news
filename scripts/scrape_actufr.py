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
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
}

def get_db_connection():
    clean_url = DATABASE_URL.replace("?pgbouncer=true", "").replace("&pgbouncer=true", "")
    return psycopg2.connect(clean_url)

def fetch_actufr_content(url):
    try:
        time.sleep(random.uniform(0.5, 1.5))
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code != 200:
            print(f"   ⚠️ Status {response.status_code}")
            return None

        soup = BeautifulSoup(response.text, 'html.parser')
        
        text_parts = []

        # 1. Le Chapô (Premier paragraphe de .ac-article-main)
        main_header = soup.find('div', class_='ac-article-main')
        if main_header:
            chapo = main_header.find('p')
            if chapo:
                text_parts.append(chapo.get_text().strip())

        # 2. Le corps (.ac-article-content)
        content_div = soup.find('div', class_='ac-article-content')
        if content_div:
            # On nettoie les éléments indésirables
            for garbage in content_div.select('.ac-article-to-read, .ac-banner-ad, .ac-banner-article, script, style, .ac-article-date, .ac-article-actions'):
                garbage.decompose()
            
            # On récupère les paragraphes et les titres
            for element in content_div.find_all(['p', 'h2']):
                txt = element.get_text().strip()
                if txt and len(txt) > 5:
                    if "Mon Actu" not in txt and "S'incrire" not in txt:
                        text_parts.append(txt)

        if text_parts:
            # On filtre les doublons éventuels (parfois le chapo est répété)
            unique_parts = []
            for part in text_parts:
                if part not in unique_parts:
                    unique_parts.append(part)
            return "\n\n".join(unique_parts)
        
        return None

    except Exception as e:
        print(f"   ❌ Erreur fetch: {e}")
        return None

def main():
    print("[*] Démarrage du scraper dédié Actu.fr...")
    
    conn = get_db_connection()
    cur = conn.cursor()

    # Sélectionner les articles Actu.fr sans contenu
    cur.execute("""
        SELECT id, title, link 
        FROM \"Article\" 
        WHERE (link LIKE '%actu.fr%' OR source LIKE '%Actu.fr%')
          AND (content IS NULL OR LENGTH(content) < 100)
    """)
    articles = cur.fetchall()
    
    if not articles:
        print("Aucun article Actu.fr à traiter.")
        return

    print(f"[*] {len(articles)} articles Actu.fr à traiter.")

    success_count = 0
    for i, (art_id, title, link) in enumerate(articles, 1):
        print(f"[{i}/{len(articles)}] {title[:50]}...")
        
        content = fetch_actufr_content(link)
        
        if content:
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
    print(f"\n[*] Terminé. {success_count} articles Actu.fr mis à jour.")

if __name__ == "__main__":
    main()
