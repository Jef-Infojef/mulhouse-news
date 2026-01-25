import os
import psycopg2
from dotenv import load_dotenv

load_dotenv(".env.local")
DATABASE_URL = os.environ.get("NEWS_DATABASE_URL")

def check_radio_france_details():
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        
        cur.execute("""
            SELECT id, title, "imageUrl", "description"
            FROM "Article" 
            WHERE source LIKE '%Radio France%'
              AND (("imageUrl" IS NULL OR "imageUrl" = '') OR ("description" IS NULL OR "description" = ''))
            LIMIT 10
        """)
        articles = cur.fetchall()
        
        print(f"--- DÉTAILS RADIO FRANCE ---")
        for art in articles:
            img_status = "OK" if art[2] and len(art[2]) > 0 else "MANQUANTE"
            desc_status = "OK" if art[3] and len(art[3]) > 0 else "MANQUANTE"
            print(f"Titre: {art[1][:50]}...")
            print(f"  > Image: {img_status}")
            print(f"  > Desc : {desc_status}")
            if art[3]:
                print(f"  > Aperçu Desc: {art[3][:100]}...")
            print("-" * 30)

        cur.close()
        conn.close()
    except Exception as e:
        print(f"Erreur : {e}")

if __name__ == "__main__":
    check_radio_france_details()
