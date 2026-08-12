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

def fetch_alterpresse_content(url):
    try:
        time.sleep(random.uniform(0.5, 1.5))
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code != 200:
            print(f"   ⚠️ Status {response.status_code}")
            return None

        soup = BeautifulSoup(response.text, 'html.parser')
        
        text_parts = []

        # Sur L'Alterpresse68, le contenu est dans .entry-content
        content_div = soup.find('div', class_='entry-content')
        
        if content_div:
            # On nettoie les éléments indésirables
            # (Blocs de dons, widgets donorbox, tags de fin, scripts)
            for garbage in content_div.select('script, style, .wp-block-spacer, dbox-widget, .sharedaddy, .important'):
                garbage.decompose()
            
            # On récupère les paragraphes et les titres
            for element in content_div.find_all(['p', 'h2', 'h3', 'h4']):
                txt = element.get_text().strip()
                # On évite le texte de don récurent à la fin
                if "Soutenez-nous par un ou des dons" in txt or "Lectrices et lecteurs" in txt:
                    continue
                if txt and len(txt) > 5:
                    text_parts.append(txt)

        if text_parts:
            return "\n\n".join(text_parts)
        
        return None

    except Exception as e:
        print(f"   ❌ Erreur fetch: {e}")
        return None

def main():
    print("[*] Démarrage du scraper dédié L'Alterpresse68...")
    
    conn = get_db_connection()
    cur = conn.cursor()

    # Sélectionner les articles Alterpresse sans contenu
    cur.execute("""
        SELECT id, title, link 
        FROM \"Article\" 
        WHERE (link LIKE '%alterpresse68.info%' OR source LIKE '%Alterpresse%')
          AND (content IS NULL OR LENGTH(content) < 100)
    """)
    articles = cur.fetchall()
    
    if not articles:
        print("Aucun article Alterpresse à traiter.")
        return

    print(f"[*] {len(articles)} articles Alterpresse à traiter.")

    success_count = 0
    for i, (art_id, title, link) in enumerate(articles, 1):
        print(f"[{i}/{len(articles)}] {title[:50]}...")
        
        content = fetch_alterpresse_content(link)
        
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
    print(f"\n[*] Terminé. {success_count} articles Alterpresse mis à jour.")

if __name__ == "__main__":
    main()
