import os
from curl_cffi import requests
from bs4 import BeautifulSoup
import re
import html
import psycopg2
from dotenv import load_dotenv
import time
import random

# Charger les variables d'environnement
load_dotenv(".env.local")
DATABASE_URL = os.environ.get("NEWS_DATABASE_URL")

def get_db_connection():
    return psycopg2.connect(DATABASE_URL)

def fetch_og_data(url):
    """Tente de récupérer og:image et description avec curl_cffi et BeautifulSoup"""
    if not url or "google.com" in url:
        return None, None
        
    try:
        # On simule un délai humain
        time.sleep(random.uniform(1, 3))
        
        # Utilisation de curl_cffi pour contourner les protections (TLS, WAF)
        resp = requests.get(url, impersonate="chrome110", timeout=15, allow_redirects=True)
        
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, 'html.parser')
            
            # 1. Extraction Image (og:image)
            img = None
            og_image = soup.find("meta", property="og:image")
            if og_image and og_image.get("content"):
                img = html.unescape(og_image["content"])
            
            # Fallback Twitter Image
            if not img:
                tw_image = soup.find("meta", attrs={"name": "twitter:image"})
                if tw_image and tw_image.get("content"):
                    img = html.unescape(tw_image["content"])

            # 2. Extraction Description
            desc = None
            og_desc = soup.find("meta", property="og:description")
            if og_desc and og_desc.get("content"):
                desc = html.unescape(og_desc["content"])
            
            if not desc:
                meta_desc = soup.find("meta", attrs={"name": "description"})
                if meta_desc and meta_desc.get("content"):
                    desc = html.unescape(meta_desc["content"])

            if desc and len(desc) > 250: 
                desc = desc[:247] + "..."
                
            return img, desc
        else:
            print(f"      [!] Erreur HTTP {resp.status_code}")
    except Exception as e:
        print(f"      [!] Exception: {e}")
        
    return None, None

def main():
    print("[*] Démarrage de la réparation des articles sans photo...")
    
    conn = get_db_connection()
    cur = conn.cursor()
    
    # On cible les articles sans photo (limité à 50 pour le test)
    # On exclut les liens google non décodés qui traîneraient
    cur.execute("""
        SELECT id, title, link, source 
        FROM "Article" 
        WHERE ("imageUrl" IS NULL OR "imageUrl" = '') 
          AND link NOT LIKE '%google.com%'
        ORDER BY "publishedAt" DESC
    """)
    articles = cur.fetchall()
    
    print(f"[*] {len(articles)} articles à tenter de réparer.")
    
    success_count = 0
    
    for art_id, title, link, source in articles:
        print(f"\nTentative pour: {title[:60]}...")
        print(f"  -> Source: {source} | URL: {link[:50]}...")
        
        new_img, new_desc = fetch_og_data(link)
        
        if new_img or new_desc:
            try:
                if new_img and new_desc:
                    cur.execute("UPDATE \"Article\" SET \"imageUrl\" = %s, \"description\" = %s WHERE id = %s", (new_img, new_desc, art_id))
                elif new_img:
                    cur.execute("UPDATE \"Article\" SET \"imageUrl\" = %s WHERE id = %s", (new_img, art_id))
                elif new_desc:
                    cur.execute("UPDATE \"Article\" SET \"description\" = %s WHERE id = %s", (new_desc, art_id))
                
                conn.commit()
                success_count += 1
                print(f"  -> ✅ SUCCÈS ! Image: {bool(new_img)}, Desc: {bool(new_desc)}")
            except Exception as e:
                conn.rollback()
                print(f"  -> ❌ Erreur DB: {e}")
        else:
            print("  -> ❌ Échec (bloqué ou non trouvé)")

    print(f"\n[*] Travail terminé. {success_count} articles ont été réparés.")
    cur.close()
    conn.close()

if __name__ == "__main__":
    main()
