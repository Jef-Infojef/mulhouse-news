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

# URL relative trouvée dans la DB, on doit la reconstruire pour le fetch
relative_link = "/d/municipales-2026-apres-six-ans-de-mandat-quel-bilan-pour-les-maires-des-principales-villes-d-alsace-832a257d-5d36-4155-985c-b9159afe278a"
full_url = "https://www.dna.fr" + relative_link

def fix_dna_article():
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        print(f"Analyse de l'article DNA : {full_url}")
        response = requests.get(full_url, headers=headers, timeout=15)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Récupération du vrai titre via og:title ou h1
        og_title = soup.find("meta", property="og:title")
        real_title = og_title.get('content') if og_title else None
        
        if not real_title:
            h1 = soup.find("h1")
            real_title = h1.get_text().strip() if h1 else None
            
        # Récupération de la description
        og_desc = soup.find("meta", property="og:description")
        desc = og_desc.get('content') if og_desc else None
        
        # Récupération de l'image
        og_image = soup.find("meta", property="og:image")
        img = og_image.get('content') if og_image else None

        if real_title:
            print(f"Vrai titre trouvé : {real_title}")
            conn = get_db_connection()
            cur = conn.cursor()
            
            # Mise à jour avec le lien relatif tel qu'il est dans la DB
            cur.execute('''
                UPDATE "Article" 
                SET title = %s, description = %s, "imageUrl" = %s 
                WHERE link = %s
            ''', (real_title, desc, img, relative_link))
            
            conn.commit()
            cur.close()
            conn.close()
            print("✅ Article DNA mis à jour avec succès !")
        else:
            print("❌ Impossible de trouver le vrai titre.")

    except Exception as e:
        print(f"Erreur : {e}")

fix_dna_article()
