import os
import psycopg2
from dotenv import load_dotenv

load_dotenv(".env.local")
DATABASE_URL = os.environ.get("NEWS_DATABASE_URL")

def diagnose_ebra():
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        
        # Récupérer un des articles problématiques
        cur.execute("""
            SELECT id, title, link, "imageUrl", "description"
            FROM "Article" 
            WHERE (source LIKE '%Alsace%' OR source LIKE '%DNA%')
              AND (("imageUrl" IS NULL OR "imageUrl" = '') OR ("description" IS NULL OR "description" = ''))
              AND link NOT LIKE '%google.com%'
            LIMIT 1
        """)
        art = cur.fetchone()
        
        if art:
            print(f"ID: {art[0]}")
            print(f"Titre: {art[1]}")
            print(f"Lien: {art[2]}")
            print(f"Image actuelle: '{art[3]}'")
            print(f"Description actuelle: '{art[4]}'")
        else:
            print("Aucun article problématique trouvé (bizarre).")

        cur.close()
        conn.close()
    except Exception as e:
        print(f"Erreur : {e}")

if __name__ == "__main__":
    diagnose_ebra()
