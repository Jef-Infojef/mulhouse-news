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

def fetch_periscope_content(url):
    try:
        time.sleep(random.uniform(0.5, 1.5))
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code != 200:
            print(f"   ⚠️ Status {response.status_code}")
            return None

        soup = BeautifulSoup(response.text, 'html.parser')
        
        text_parts = []

        # Sur le Périscope, le contenu est dans le flux principal après le titre
        # On cherche l'article ou le main
        article_body = soup.find('article') or soup.find('main')
        
        if article_body:
            # On cherche les paragraphes et les sous-titres
            # Les articles Gutenberg utilisent souvent des paragraphes directs
            # On exclut les éléments de partage et les métadonnées (date, édition)
            elements = article_body.find_all(['p', 'h2'])
            for el in elements:
                # On ignore les paragraphes de métadonnées (commençant par "Édition :")
                txt = el.get_text().strip()
                if txt and len(txt) > 5:
                    if not txt.startswith("Édition :") and "addtoany" not in str(el).lower():
                        text_parts.append(txt)

        if text_parts:
            # On filtre les doublons éventuels et on joint
            return "\n\n".join(text_parts)
        
        return None

    except Exception as e:
        print(f"   ❌ Erreur fetch: {e}")
        return None

def main():
    print("[*] Démarrage du scraper dédié Le Périscope...")
    
    conn = get_db_connection()
    cur = conn.cursor()

    # Sélectionner les articles Le Périscope sans contenu
    cur.execute("""
        SELECT id, title, link 
        FROM \"Article\" 
        WHERE link LIKE '%le-periscope.info%' 
          AND (content IS NULL OR LENGTH(content) < 100)
    """)
    articles = cur.fetchall()
    
    if not articles:
        print("Aucun article Le Périscope à traiter.")
        return

    print(f"[*] {len(articles)} articles Le Périscope à traiter.")

    success_count = 0
    for i, (art_id, title, link) in enumerate(articles, 1):
        print(f"[{i}/{len(articles)}] {title[:50]}...")
        
        content = fetch_periscope_content(link)
        
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
    print(f"\n[*] Terminé. {success_count} articles Le Périscope mis à jour.")

if __name__ == "__main__":
    main()
