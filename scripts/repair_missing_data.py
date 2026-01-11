import os
import requests
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
    """Tente de récupérer og:image et description avec un User-Agent robuste"""
    if not url or "google.com" in url:
        return None, None
        
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
        'Accept-Language': 'fr-FR,fr;q=0.9,en-US;q=0.8,en;q=0.7',
        'Cache-Control': 'no-cache',
        'Pragma': 'no-cache',
    }
    
    try:
        # On simule un délai humain
        time.sleep(random.uniform(1, 3))
        resp = requests.get(url, headers=headers, timeout=15, allow_redirects=True)
        
        if resp.status_code == 200:
            html_content = resp.text
            
            # 1. Extraction Image
            img = None
            # Pattern standard
            m_img = re.search(r'property=["\']og:image["\'][^>]*content=["\']([^"\']+)["\']', html_content)
            if not m_img:
                m_img = re.search(r'content=["\']([^"\']+)["\'][^>]*property=["\']og:image["\']', html_content)
            
            if m_img:
                img = html.unescape(m_img.group(1))
            
            # 2. Extraction Description
            desc = None
            m_desc = re.search(r'property=["\']og:description["\'][^>]*content=["\']([^"\']+)["\']', html_content)
            if not m_desc:
                m_desc = re.search(r'name=["\']description["\'][^>]*content=["\']([^"\']+)["\']', html_content)
            
            if m_desc:
                desc = html.unescape(m_desc.group(1))
                if len(desc) > 250: desc = desc[:247] + "..."
                
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
