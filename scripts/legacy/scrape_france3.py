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

def fetch_france3_content(url):
    try:
        time.sleep(random.uniform(0.5, 1.5))
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code != 200:
            print(f"   ⚠️ Status {response.status_code}")
            return None

        soup = BeautifulSoup(response.text, 'html.parser')
        
        text_parts = []

        # 1. L'Intro (article__intro)
        intro = soup.find('p', class_='article__intro')
        if intro:
            text_parts.append(intro.get_text().strip())

        # 2. Le Corps
        # Sur France Info, le corps est souvent composé de paragraphes directs 
        # dans un conteneur ou à la suite de l'intro.
        # On cherche d'abord s'il y a un conteneur dédié
        body_container = soup.find('div', class_='article__body') or \
                         soup.find('div', class_='entry-content') or \
                         soup.find('div', class_='content')

        if body_container:
            # On nettoie les éléments indésirables (newsletters, pubs)
            for garbage in body_container.select('.optin-newsletter-main, .ads, script, style, .article-image__container'):
                garbage.decompose()
            
            # On récupère les paragraphes et les sous-titres
            for element in body_container.find_all(['p', 'h2']):
                txt = element.get_text().strip()
                if txt and len(txt) > 5:
                    text_parts.append(txt)
        else:
            # Fallback si pas de conteneur : on prend les paragraphes après l'intro
            # (Plus risqué mais utile parfois)
            pass

        if text_parts:
            # Filtrage des doublons si l'intro est répétée dans le corps
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
    print("[*] Démarrage du scraper dédié France 3 Régions...")
    
    conn = get_db_connection()
    cur = conn.cursor()

    # Sélectionner les articles France 3 sans contenu
    cur.execute("""
        SELECT id, title, link 
        FROM \"Article\" 
        WHERE source ILIKE '%France 3%' 
          AND (content IS NULL OR LENGTH(content) < 100)
    """)
    articles = cur.fetchall()
    
    if not articles:
        print("Aucun article France 3 à traiter.")
        return

    print(f"[*] {len(articles)} articles France 3 à traiter.")

    success_count = 0
    for i, (art_id, title, link) in enumerate(articles, 1):
        print(f"[{i}/{len(articles)}] {title[:50]}...")
        
        content = fetch_france3_content(link)
        
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
    print(f"\n[*] Terminé. {success_count} articles France 3 mis à jour.")

if __name__ == "__main__":
    main()
