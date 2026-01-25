import os
import requests
import re
import html
import psycopg2
from bs4 import BeautifulSoup
from dotenv import load_dotenv
import time

# Configuration
def load_env():
    root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    env_files = [".envenv", ".env.local", ".env"]
    for f in env_files:
        path = os.path.join(root_dir, f)
        if os.path.exists(path):
            load_dotenv(path)
            if os.environ.get("DATABASE_URL"): break

load_env()
DATABASE_URL = os.environ.get("DATABASE_URL")

# Le cookie fourni par l'utilisateur
COOKIES_RAW = ".XCONNECT_SESSION=2=42F647DB9B788CF4E0AFFF1DD52DE98DAC09560B7B8173B6AE707DE13249B5D3D98E26C37209690D989A05961C1E93CBDDF2909ED6FF95194BEA6AE2C1E5A62F519DB83384CA795ACE1E2824AA4C1D00C904F51699D03E6489E9A4B4C8211E0D25B9B66E68555AA3B098E18D1CFB0D8E55CD162A101CF8E23306F0A225ABBE4E6AA1480CEA97DAEF016F99185FECA69B74DCE53DE2A59FB8889A43374A7891008D274391E153481FAF94E8CF51E25A9872DE0D0AA146142A059E319D5BEC9708926A8C25B1A97FBA849A2B64CC973B6CE3700E3E16AB420B9135DE775FE8D9E4AF4D143969441F03400814963FB3C265; .XCONNECTKeepAlive=2=1; .XCONNECT=2=1; _poool=9aab6ee3-fda6-43fc-a90e-29de3c73d8f7"

cookies = {}
for part in COOKIES_RAW.split(';'):
    if '=' in part:
        key, value = part.strip().split('=', 1)
        cookies[key] = value

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
}

def get_db_connection():
    url = DATABASE_URL
    if url and "?pgbouncer=true" in url:
        url = url.replace("?pgbouncer=true", "")
    return psycopg2.connect(url)

def fetch_og_image(session, url):
    try:
        resp = session.get(url, timeout=10)
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, 'html.parser')
            # 1. Meta OG Image
            meta_img = soup.find('meta', property='og:image') or soup.find('meta', attrs={'name': 'twitter:image'})
            if meta_img and meta_img.get('content'):
                return meta_img['content']
            
            # 2. LD+JSON Image
            import json
            for script in soup.find_all('script', type='application/ld+json'):
                try:
                    data = json.loads(script.string)
                    items = data if isinstance(data, list) else [data]
                    for item in items:
                        if 'image' in item:
                            img = item['image']
                            if isinstance(img, dict) and 'url' in img: return img['url']
                            if isinstance(img, str): return img
                            if isinstance(img, list) and len(img) > 0: return img[0]
                except: pass
    except Exception as e:
        print(f"    [!] Erreur fetch: {e}")
    return None

def main():
    print("[*] Démarrage de la récupération des images manquantes...")
    
    session = requests.Session()
    session.headers.update(headers)
    for key, value in cookies.items():
        session.cookies.set(key, value, domain=".lalsace.fr")

    conn = get_db_connection()
    cur = conn.cursor()
    
    cur.execute("""
        SELECT id, title, link, "imageUrl" 
        FROM "Article" 
        WHERE ("imageUrl" IS NULL OR "imageUrl" = '')
          AND link LIKE '%lalsace.fr%'
        ORDER BY "publishedAt" DESC
    """)
    articles = cur.fetchall()
    
    if not articles:
        print("Aucun article sans image à traiter.")
        return

    print(f"[*] {len(articles)} articles à traiter.")
    updated_count = 0
    
    for i, (art_id, title, link, current_image) in enumerate(articles, 1):
        print(f"[{i}/{len(articles)}] {title[:50]}...")
        
        image_url = fetch_og_image(session, link)
        
        if image_url:
            print(f"  -> ✅ Image trouvée : {image_url[:80]}...")
            try:
                cur.execute('UPDATE "Article" SET "imageUrl" = %s WHERE id = %s', (image_url, art_id))
                conn.commit()
                updated_count += 1
            except Exception as e:
                conn.rollback()
                print(f"  -> ❌ Erreur DB : {e}")
        else:
            print("  -> ⚠️ Pas d'image.")
            
        time.sleep(0.5)

    print(f"\n[*] Terminé. {updated_count} images récupérées.")
    cur.close()
    conn.close()

if __name__ == "__main__":
    main()
