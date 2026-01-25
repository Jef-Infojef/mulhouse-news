import os
import psycopg2
from dotenv import load_dotenv

load_dotenv(".env.local")
DATABASE_URL = os.environ.get("NEWS_DATABASE_URL")

def list_les_echos_links():
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        
        cur.execute("""
            SELECT title, link, "publishedAt"
            FROM "Article" 
            WHERE source LIKE '%Echos%'
              AND (("imageUrl" IS NULL OR "imageUrl" = '') OR ("description" IS NULL OR "description" = ''))
            ORDER BY "publishedAt" DESC
            LIMIT 10
        """)
        articles = cur.fetchall()
        
        print(f"--- 10 Derniers articles Les Echos manquants ---")
        for i, (title, link, pub_date) in enumerate(articles, 1):
            date_str = pub_date.strftime('%d/%m/%Y') if pub_date else "Date inconnue"
            print(f"{i}. [{date_str}] {title}")
            print(f"   {link}\n")

        cur.close()
        conn.close()
    except Exception as e:
        print(f"Erreur : {e}")

if __name__ == "__main__":
    list_les_echos_links()

