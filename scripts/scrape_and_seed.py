import os
import requests
import xml.etree.ElementTree as ET
import re
from datetime import datetime
from email.utils import parsedate_to_datetime
from googlenewsdecoder import gnewsdecoder
import psycopg2
from psycopg2 import sql
from dotenv import load_dotenv

# Charger les variables d'environnement depuis le fichier .env
load_dotenv()

# Configuration
DATABASE_URL = os.environ.get("DATABASE_URL")
RSS_URL = "https://news.google.com/rss/search?q=Mulhouse&hl=fr&gl=FR&ceid=FR:fr"

def get_db_connection():
    if not DATABASE_URL:
        raise Exception("DATABASE_URL non définie")
    try:
        return psycopg2.connect(DATABASE_URL)
    except Exception as e:
        # Si l'URL est au format Prisma (prisma+postgres://), psycopg2 ne va pas aimer.
        raise Exception(f"Erreur de connexion DB (URL invalide ou serveur injoignable): {e}")

def extract_real_url(google_url):
    try:
        decoded = gnewsdecoder(google_url)
        if decoded.get("status"):
            return decoded["decoded_url"]
    except Exception as e:
        print(f"    [!] Erreur de décodage: {e}")
    return google_url

def fetch_og_image(url):
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        resp = requests.get(url, headers=headers, timeout=10)
        if resp.status_code == 200:
            match = re.search(r'<meta\s+property=["\']og:image["\']\s+content=["\']([^"\\]+)["\\]', resp.text, re.IGNORECASE)
            if match:
                return match.group(1)
    except Exception:
        pass
    return None

def main():
    print("[*] Démarrage du scraping Google News...")
    
    # 1. Récupération du RSS
    try:
        resp = requests.get(RSS_URL, timeout=15)
        if resp.status_code != 200:
            print(f"[!] Erreur RSS: {resp.status_code}")
            exit(1)
    except Exception as e:
        print(f"[!] Exception lors de la récupération RSS: {e}")
        exit(1)
        
    try:
        root = ET.fromstring(resp.content)
        items = root.findall(".//item")
    except Exception as e:
        print(f"[!] Erreur parsing XML: {e}")
        exit(1)

    print(f"[+] {len(items)} articles trouvés dans le RSS.")
    
    conn = None
    cur = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        print("[*] Connexion base de données : OK")
    except Exception as e:
        print(f"[!] Impossible de se connecter à la base de données : {e}")
        print("[*] Passage en mode SIMULATION (pas d'écriture en base)")
        cur = None
    
    new_count = 0
    
    for item in items[:100]: # Traiter jusqu'à 100 articles (le max du RSS)
        title_elem = item.find("title")
        link_elem = item.find("link")
        pub_elem = item.find("pubDate")
        src_elem = item.find("source")

        title = title_elem.text if title_elem is not None else "Sans titre"
        google_link = link_elem.text if link_elem is not None else ""
        pub_date_str = pub_elem.text if pub_elem is not None else ""
        source = src_elem.text if src_elem is not None else "Inconnu"
        
        if not google_link:
            continue

        # Convert date
        try:
            pub_date = parsedate_to_datetime(pub_date_str)
        except:
            pub_date = datetime.now()

        print(f"\nTraitement: {title}")
        
        # 2. Obtenir l'URL réelle
        real_url = extract_real_url(google_link)
        print(f"  -> URL: {real_url}")
        
        if cur:
            # Vérifier si existe déjà
            try:
                cur.execute("SELECT id FROM \"Article\" WHERE link = %s", (real_url,))
                if cur.fetchone():
                    print("  -> Déjà en base. Ignoré.")
                    continue
            except Exception as e:
                print(f"  -> [!] Erreur lecture DB: {e}")
                conn.rollback() # Reset transaction
        
        # 3. Récupérer l'image
        image_url = fetch_og_image(real_url)
        print(f"  -> Image: {image_url if image_url else 'Aucune'}")
        
        # 4. Insertion
        if cur:
            try:
                cur.execute("""
                    INSERT INTO \"Article\" (id, title, link, \"imageUrl\", source, \"publishedAt\", \"updatedAt\")
                    VALUES (gen_random_uuid(), %s, %s, %s, %s, %s, NOW())
                """, (title, real_url, image_url, source, pub_date))
                conn.commit()
                new_count += 1
                print("  -> [+] Inséré !")
            except Exception as e:
                conn.rollback()
                print(f"  -> [!] Erreur insertion: {e}")
        else:
            print("  -> [SIMULATION] Article prêt à être inséré.")

    print(f"\n[*] Terminé. {new_count} nouveaux articles ajoutés.")
    if conn:
        cur.close()
        conn.close()

if __name__ == "__main__":
    main()