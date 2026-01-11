import os
import requests
import xml.etree.ElementTree as ET
import re
import html
from datetime import datetime
from email.utils import parsedate_to_datetime
from googlenewsdecoder import gnewsdecoder
import psycopg2
from psycopg2 import sql
from dotenv import load_dotenv
import time
import random

# Charger les variables d'environnement
load_dotenv(".env.local")

# Configuration
DATABASE_URL = os.environ.get("DATABASE_URL")
RSS_URL = "https://news.google.com/rss/search?q=Mulhouse&hl=fr&gl=FR&ceid=FR:fr"
MAX_CONSECUTIVE_DECODE_ERRORS = 3  # Arrêt si trop d'échecs de décodage (IP bannie)

def get_db_connection():
    if not DATABASE_URL:
        raise Exception("DATABASE_URL non définie")
    return psycopg2.connect(DATABASE_URL)

def extract_real_url(google_url):
    """Tente de décoder l'URL Google News"""
    try:
        decoded = gnewsdecoder(google_url)
        if decoded.get("status"):
            return decoded["decoded_url"]
        else:
            print(f"    [!] Échec décodage Google: {decoded.get('message', 'Erreur inconnue')}")
    except Exception as e:
        print(f"    [!] Exception décodage: {e}")
    return google_url

def fetch_content_data(url):
    """Récupère l'image OG et la description avec un User-Agent robuste"""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
        'Accept-Language': 'fr-FR,fr;q=0.9,en-US;q=0.8,en;q=0.7',
    }
    
    img, desc = None, None
    try:
        resp = requests.get(url, headers=headers, timeout=12, allow_redirects=True)
        if resp.status_code == 200:
            content = resp.text
            # Extraction Image
            m_img = re.search(r'property=["\"]og:image["\"][^>]*content=["\"]([^"\"]+)["\"]', content)
            if not m_img: m_img = re.search(r'content=["\"]([^"\"]+)["\"][^>]*property=["\"]og:image["\"]', content)
            if m_img: img = html.unescape(m_img.group(1))
            
            # Extraction Description
            m_desc = re.search(r'property=["\"]og:description["\"][^>]*content=["\"]([^"\"]+)["\"]', content)
            if not m_desc: m_desc = re.search(r'name=["\"]description["\"][^>]*content=["\"]([^"\"]+)["\"]', content)
            if m_desc:
                desc = html.unescape(m_desc.group(1))
                if len(desc) > 250: desc = desc[:247] + "..."
        else:
            print(f"    [!] Erreur HTTP {resp.status_code} sur le média")
    except Exception:
        pass
    return img, desc

def main():
    print(f"[*] Démarrage Mulhouse Actu Scraper - {datetime.now().strftime('%H:%M:%S')}")
    
    try:
        resp = requests.get(RSS_URL, timeout=15)
        root = ET.fromstring(resp.content)
        items = root.findall(".//item")
    except Exception as e:
        print(f"[!] Erreur RSS: {e}")
        return

    print(f"[+] {len(items)} articles trouvés dans le RSS.")
    
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
    except Exception as e:
        print(f"[!] Erreur DB: {e}")
        return

    new_count = 0
    consecutive_decode_errors = 0
    
    for item in items[:100]:
        title = item.find("title").text or "Sans titre"
        google_link = item.find("link").text or ""
        pub_date_str = item.find("pubDate").text or ""
        source = item.find("source").text or "Inconnu"
        
        if not google_link: continue

        # 1. Décodage obligatoire
        real_url = extract_real_url(google_link)

        # 2. Vérifier si déjà en base
        cur.execute("SELECT id FROM \"Article\" WHERE link = %s", (real_url,))
        if cur.fetchone():
            continue

        print(f"\nNouveau: {title[:70]}")
        
        # 3. Récupération métadonnées (Image + Description)
        # On attend un peu pour ne pas brusquer les médias
        time.sleep(random.uniform(0.5, 1.5))
        image_url, description = fetch_content_data(real_url)
        
        # 4. Insertion
        try:
            cur.execute("""
                INSERT INTO \"Article\" (id, title, link, \"imageUrl\", source, description, \"publishedAt\", \"updatedAt\")
                VALUES (gen_random_uuid(), %s, %s, %s, %s, %s, %s, NOW())
            """, (title, real_url, image_url, source, description, parsedate_to_datetime(pub_date_str)))
            conn.commit()
            new_count += 1
            print(f"  -> [+] Inséré (Img: {bool(image_url)}, Desc: {bool(description)})")
        except Exception as e:
            conn.rollback()
            print(f"  -> [!] Erreur insertion: {e}")

    print(f"\n[*] Terminé. {new_count} articles ajoutés.")
    cur.close()
    conn.close()

if __name__ == "__main__":
    main()
