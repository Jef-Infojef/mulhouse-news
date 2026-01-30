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

url = "https://livrenoir.fr/divers/mulhouse-une-sculpture-de-voiture-de-police-detruite-par-des-etudiants-le-prefet-saisit-la-justic---15148"

try:
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    # Utilisation de verify=False car certains sites ont des soucis de certificats avec requests
    response = requests.get(url, headers=headers, timeout=15, verify=False)
    soup = BeautifulSoup(response.text, 'html.parser')
    
    og_image = soup.find("meta", property="og:image")
    img_url = og_image.get('content') if og_image else None
    
    if img_url:
        print(f"Image identifiée : {img_url}")
        conn = get_db_connection()
        cur = conn.cursor()
        
        cur.execute('UPDATE "Article" SET "imageUrl" = %s WHERE link = %s', (img_url, url))
        conn.commit()
        
        print("✅ Base de données mise à jour avec succès via Python/SQL !")
        cur.close()
        conn.close()
    else:
        print("❌ Impossible de trouver l'image même avec Python.")

except Exception as e:
    print(f"Erreur : {e}")
