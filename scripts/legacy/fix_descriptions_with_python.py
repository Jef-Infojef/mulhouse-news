import os
import requests
from bs4 import BeautifulSoup
import psycopg2
from dotenv import load_dotenv

load_dotenv(".env.local")
DATABASE_URL = os.environ.get("DATABASE_URL")

def get_db_connection():
    clean_url = DATABASE_URL.replace("?pgbouncer=true", "").replace("&pgbouncer=true", "")
    return psycopg2.connect(clean_url)

articles_to_fix = [
    "https://livrenoir.fr/divers/mulhouse-une-sculpture-de-voiture-de-police-detruite-par-des-etudiants-le-prefet-saisit-la-justic---15148",
    "https://fr.news.yahoo.com/mulhouse-pi%C3%B1ata-voiture-police-%C3%A9ventr%C3%A9e-165126563.html"
]

def fix_article(url):
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        response = requests.get(url, headers=headers, timeout=15, verify=False)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        og_desc = soup.find("meta", property="og:description")
        desc = og_desc.get('content') if og_desc else None
        
        if not desc:
            meta_desc = soup.find("meta", attrs={"name": "description"})
            desc = meta_desc.get('content') if meta_desc else None

        if desc:
            print(f"Description trouvée pour {url[:40]}... : {desc[:100]}...")
            conn = get_db_connection()
            cur = conn.cursor()
            cur.execute('UPDATE "Article" SET description = %s WHERE link = %s', (desc, url))
            conn.commit()
            cur.close()
            conn.close()
            return True
        else:
            print(f"❌ Aucune description trouvée pour {url}")
            return False

    except Exception as e:
        print(f"Erreur pour {url}: {e}")
        return False

for url in articles_to_fix:
    fix_article(url)
