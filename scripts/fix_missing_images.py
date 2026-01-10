import os
import requests
import re
import html
import psycopg2
from dotenv import load_dotenv
import time

# Charger les variables d'environnement
load_dotenv()

DATABASE_URL = os.environ.get("DATABASE_URL")

def get_db_connection():
    if not DATABASE_URL:
        raise Exception("DATABASE_URL non définie")
    return psycopg2.connect(DATABASE_URL)

def fetch_og_image(url):
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        resp = requests.get(url, headers=headers, timeout=10)
        if resp.status_code == 200:
            # Pattern 1
            match1 = re.search(r'<meta\s+[^>]*property=["\']og:image["\'][^>]*content=["\']([^"\"]+)["\"]', resp.text, re.IGNORECASE)
            if match1:
                return html.unescape(match1.group(1))
            
            # Pattern 2
            match2 = re.search(r'<meta\s+[^>]*content=["\']([^"\"]+)["\"][^>]*property=["\']og:image["\"]', resp.text, re.IGNORECASE)
            if match2:
                return html.unescape(match2.group(1))
    except Exception as e:
        print(f"    [!] Erreur fetch: {e}")
    return None

def main():
    print("[*] Démarrage de la réparation des images...")
    
    conn = get_db_connection()
    cur = conn.cursor()
    
    # On cherche aussi les articles LNV spécifiquement pour forcer une mise à jour si l'URL contient &amp;
    cur.execute("SELECT id, title, link, \"imageUrl\" FROM \"Article\" WHERE link LIKE '%lnv.fr%' OR \"imageUrl\" IS NULL OR \"imageUrl\" = ''")
    articles = cur.fetchall()
    
    print(f"[*] {len(articles)} articles à vérifier (LNV ou sans image).")
    
    updated_count = 0
    
    for article in articles:
        art_id, title, link, current_image = article
        
        # Si c'est LNV et qu'on a déjà une image potentiellement "sale" (avec &amp;)
        # OU si pas d'image du tout
        needs_update = False
        
        if not current_image:
            needs_update = True
        elif "lnv.fr" in link and "&amp;" in current_image:
            needs_update = True
            
        if not needs_update:
            continue

        print(f"\nTraitement: {title[:50]}...")
        print(f"  -> Link: {link}")
        
        image_url = fetch_og_image(link)
        
        if image_url:
            # Vérif si changement réel
            if image_url != current_image:
                print(f"  -> Nouvelle image: {image_url}")
                try:
                    cur.execute("UPDATE \"Article\" SET \"imageUrl\" = %s WHERE id = %s", (image_url, art_id))
                    conn.commit()
                    updated_count += 1
                    print("  -> Mise à jour OK.")
                except Exception as e:
                    conn.rollback()
                    print(f"  -> Erreur update DB: {e}")
            else:
                print("  -> Image identique, pas de changement.")
        else:
            print("  -> Pas d'image trouvée.")
            
        time.sleep(0.5)

    print(f"\n[*] Terminé. {updated_count} articles mis à jour.")
    cur.close()
    conn.close()

if __name__ == "__main__":
    main()