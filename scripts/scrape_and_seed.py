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
load_dotenv()

# Configuration
DATABASE_URL = os.environ.get("DATABASE_URL")
RSS_URL = "https://news.google.com/rss/search?q=Mulhouse&hl=fr&gl=FR&ceid=FR:fr"
MAX_CONSECUTIVE_DECODE_ERRORS = 3

def get_db_connection():
    if not DATABASE_URL:
        raise Exception("DATABASE_URL non définie")
    clean_url = DATABASE_URL.replace("?pgbouncer=true", "").replace("&pgbouncer=true", "")
    return psycopg2.connect(clean_url)

def extract_real_url(google_url):
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
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
        'Accept-Language': 'fr-FR,fr;q=0.9,en-US;q=0.8,en;q=0.7',
    }
    img, desc = None, None
    try:
        resp = requests.get(url, headers=headers, timeout=12, allow_redirects=True)
        if resp.status_code == 200:
            html_c = resp.text
            # Image
            m_img = re.search(r'property=["\"]og:image["\"][^>]*content=["\"]([^"\"]+)["\"]', html_c)
            if not m_img: m_img = re.search(r'content=["\"]([^"\"]+)["\"][^>]*property=["\"]og:image["\"]', html_c)
            if m_img: img = html.unescape(m_img.group(1))
            # Description
            m_desc = re.search(r'property=["\"]og:description["\"][^>]*content=["\"]([^"\"]+)["\"]', html_c)
            if not m_desc: m_desc = re.search(r'name=["\"]description["\"][^>]*content=["\"]([^"\"]+)["\"]', html_c)
            if m_desc: desc = html.unescape(m_desc.group(1))
    except Exception: pass
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

        # Filtrage Météo Ouest-France (souvent inutile/redondant)
        if "ouest-france" in source.lower() and "météo" in title.lower():
            print(f"    [-] Ignoré (Météo Ouest-France): {title[:40]}...")
            continue

        # 1. Décodage sécurisé
        real_url = extract_real_url(google_link)
        if "google.com" in real_url:
            consecutive_decode_errors += 1
            print(f"    [!] REJET : Lien non décodé pour '{title[:40]}...' ({consecutive_decode_errors}/{MAX_CONSECUTIVE_DECODE_ERRORS})")
            if consecutive_decode_errors >= MAX_CONSECUTIVE_DECODE_ERRORS:
                print("[!!!] ARRÊT D'URGENCE : Trop d'échecs de décodage.")
                break
            continue
        consecutive_decode_errors = 0

        # 2. Vérifier doublon (Lien OU Titre récent)
        cur.execute("SELECT id FROM \"Article\" WHERE link = %s", (real_url,))
        if cur.fetchone(): continue

        # Vérification par titre sur les 48 dernières heures (pour éviter les doublons multisources)
        cur.execute("SELECT id FROM \"Article\" WHERE title = %s AND \"publishedAt\" > NOW() - INTERVAL '48 hours'", (title,))
        if cur.fetchone():
            # print(f"    [-] Doublon titre détecté: {title[:40]}...")
            continue

        print(f"\nNouveau: {title[:70]}")
        time.sleep(random.uniform(0.5, 1.5))
        img, desc = fetch_content_data(real_url)
        
        # 3. Insertion
        try:
            cur.execute("""
                INSERT INTO \"Article\" (id, title, link, \"imageUrl\", source, description, \"publishedAt\", \"updatedAt\")
                VALUES (gen_random_uuid(), %s, %s, %s, %s, %s, %s, NOW())
            """, (title, real_url, img, source, desc, parsedate_to_datetime(pub_date_str)))
            conn.commit()
            new_count += 1
            print(f"  -> [+] Inséré (Img: {bool(img)}, Desc: {bool(desc)})")
        except Exception as e:
            conn.rollback()
            print(f"  -> [!] Erreur insertion: {e}")

    print(f"\n[*] Terminé. {new_count} articles ajoutés.")
    cur.close()
    conn.close()

if __name__ == "__main__":
    main()