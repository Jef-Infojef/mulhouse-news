import os
import requests
import re
import html
import psycopg2
from dotenv import load_dotenv
import time
import random

# Configuration
load_dotenv(".env.local")
DATABASE_URL = os.environ.get("NEWS_DATABASE_URL")

def get_db_connection():
    return psycopg2.connect(DATABASE_URL)

def fetch_description(url):
    """Tente de récupérer la description via les balises meta"""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
        'Accept-Language': 'fr-FR,fr;q=0.9,en-US;q=0.8,en;q=0.7',
    }
    
    try:
        # Délai aléatoire pour la discrétion
        time.sleep(random.uniform(0.5, 1.0))
        resp = requests.get(url, headers=headers, timeout=10, allow_redirects=True)
        
        if resp.status_code == 200:
            content = resp.text
            # Recherche og:description
            m = re.search(r'property=["\']og:description["\'][^>]*content=["\']([^"\']+)["\']', content)
            if not m:
                # Recherche meta description standard
                m = re.search(r'name=["\']description["\'][^>]*content=["\']([^"\']+)["\']', content)
            
            if m:
                desc = html.unescape(m.group(1)).strip()
                return desc if desc else None
        else:
            return f"ERR_HTTP_{resp.status_code}"
    except Exception as e:
        return f"ERR_EXCEPTION"
    return None

def main():
    print("[*] Démarrage du sauvetage des descriptions...")
    conn = get_db_connection()
    cur = conn.cursor()

    # Sélectionner les articles sans description (excluant les liens google)
    cur.execute("""
        SELECT id, title, link, source 
        FROM "Article" 
        WHERE ("description" IS NULL OR "description" = '')
          AND link NOT LIKE '%%google.com%%'
        ORDER BY "publishedAt" DESC
    """)
    articles = cur.fetchall()
    total = len(articles)
    print(f"[*] {total} articles à traiter.")

    repaired = 0
    failed = 0
    
    for i, (art_id, title, link, source) in enumerate(articles, 1):
        print(f"[{i}/{total}] {source} | {title[:50]}...")
        
        new_desc = fetch_description(link)
        
        if new_desc and not new_desc.startswith("ERR_"):
            try:
                cur.execute("UPDATE \"Article\" SET \"description\" = %s WHERE id = %s", (new_desc, art_id))
                conn.commit()
                repaired += 1
                print(f"   ✅ Description récupérée ({len(new_desc)} car.)")
            except Exception as e:
                conn.rollback()
                print(f"   ❌ Erreur DB: {e}")
        else:
            failed += 1
            reason = new_desc if new_desc and new_desc.startswith("ERR_") else "Non trouvée"
            print(f"   ⚠️ Échec: {reason}")

    cur.close()
    conn.close()
    print(f"\n[*] Bilan : {repaired} descriptions ajoutées, {failed} échecs.")

if __name__ == "__main__":
    main()
