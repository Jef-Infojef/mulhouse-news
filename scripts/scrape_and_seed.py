import os
from curl_cffi import requests
from bs4 import BeautifulSoup
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
    img, desc = None, None
    try:
        # Utilisation de impersonate pour passer outre les protections (TLS fingerprinting, etc.)
        resp = requests.get(url, timeout=20, allow_redirects=True, impersonate="chrome110")
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, 'html.parser')
            
            # Extraction Image (og:image)
            og_image = soup.find("meta", property="og:image")
            if og_image and og_image.get("content"):
                img = html.unescape(og_image["content"])
            
            # Extraction Description (og:description > description)
            og_desc = soup.find("meta", property="og:description")
            if og_desc and og_desc.get("content"):
                desc = html.unescape(og_desc["content"])
            else:
                meta_desc = soup.find("meta", attrs={"name": "description"})
                if meta_desc and meta_desc.get("content"):
                    desc = html.unescape(meta_desc["content"])
    except Exception as e:
        # print(f"Warning fetch: {e}")
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
        
        # Vérification doublon par image (si image présente et non générique)
        if img:
            placeholders = ['logo', 'placeholder', 'header', 'facebook-share', 'default', 'image.png']
            is_generic = any(p in img.lower() for p in placeholders)
            
            if not is_generic:
                # On ne bloque que si la même image a été utilisée AUJOURD'HUI
                cur.execute("""
                    SELECT id FROM \"Article\" 
                    WHERE \"imageUrl\" = %s 
                      AND \"publishedAt\"::date = %s::date
                """, (img, parsedate_to_datetime(pub_date_str)))
                if cur.fetchone():
                    print(f"    [-] Doublon image détecté pour aujourd'hui. Ignoré.")
                    continue

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