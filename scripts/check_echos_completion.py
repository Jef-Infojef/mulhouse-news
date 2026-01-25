import os
import psycopg2
from dotenv import load_dotenv

load_dotenv(".env.local")
DATABASE_URL = os.environ.get("NEWS_DATABASE_URL")

def check_echos_completion():
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        
        # Compter les articles des Echos
        cur.execute("""
            SELECT 
                COUNT(*) as total,
                COUNT("imageUrl") FILTER (WHERE "imageUrl" IS NOT NULL AND "imageUrl" != '') as has_image,
                COUNT("description") FILTER (WHERE "description" IS NOT NULL AND "description" != '') as has_desc
            FROM "Article" 
            WHERE source LIKE '%Echos%'
        """)
        stats = cur.fetchone()
        
        print(f"--- STATISTIQUES LES ECHOS ---")
        print(f"Total articles : {stats[0]}")
        print(f"Avec Image    : {stats[1]}")
        print(f"Avec Desc     : {stats[2]}")
        
        if stats[1] < stats[0] or stats[2] < stats[0]:
            print("\nCertains articles sont encore incomplets. Détails des manquants :")
            cur.execute("""
                SELECT title, "imageUrl", "description"
                FROM "Article" 
                WHERE source LIKE '%Echos%'
                  AND (("imageUrl" IS NULL OR "imageUrl" = '') OR ("description" IS NULL OR "description" = ''))
                LIMIT 5
            """)
            for row in cur.fetchall():
                img = "OK" if row[1] else "MANQUE"
                desc = "OK" if row[2] else "MANQUE"
                print(f"- {row[0][:50]}... [Img: {img}, Desc: {desc}]")

        cur.close()
        conn.close()
    except Exception as e:
        print(f"Erreur : {e}")

if __name__ == "__main__":
    check_echos_completion()
