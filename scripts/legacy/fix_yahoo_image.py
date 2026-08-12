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

url = "https://fr.news.yahoo.com/mulhouse-pi%C3%B1ata-voiture-police-%C3%A9ventr%C3%A9e-165126563.html"

def fix_yahoo_image():
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        print(f"Extraction de la vraie image Yahoo pour : {url}")
        response = requests.get(url, headers=headers, timeout=15)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Sur Yahoo, l'image principale est souvent dans une balise meta og:image 
        # mais parfois c'est le logo. On va chercher dans le corps de l'article.
        img_url = None
        
        # Tentative 1: og:image (on vérifie que ce n'est pas le logo)
        og_image = soup.find("meta", property="og:image")
        if og_image and "yahoo" not in og_image.get('content', '').lower():
            img_url = og_image.get('content')
            
        # Tentative 2: Chercher une image dans la classe "caas-img" (standard Yahoo)
        if not img_url:
            caas_img = soup.find("img", class_="caas-img")
            if caas_img:
                img_url = caas_img.get('src')
        
        # Tentative 3: N'importe quelle image large qui n'est pas un logo
        if not img_url:
            for img in soup.find_all("img"):
                src = img.get('src', '')
                if "http" in src and not any(x in src.lower() for x in ['logo', 'icon', 'pixel', 'ads']):
                    img_url = src
                    break

        if img_url:
            print(f"Vraie image trouvée : {img_url}")
            conn = get_db_connection()
            cur = conn.cursor()
            cur.execute('UPDATE "Article" SET "imageUrl" = %s WHERE link = %s', (img_url, url))
            conn.commit()
            cur.close()
            conn.close()
            print("✅ Image Yahoo mise à jour !")
        else:
            print("❌ Impossible de trouver une meilleure image que le logo.")

    except Exception as e:
        print(f"Erreur : {e}")

fix_yahoo_image()
