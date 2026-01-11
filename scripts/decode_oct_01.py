import os
import psycopg2
from googlenewsdecoder import gnewsdecoder
from dotenv import load_dotenv

load_dotenv(".env.local")

NEWS_DB_URL = os.environ.get("NEWS_DATABASE_URL")

def decode_url(google_url):
    try:
        result = gnewsdecoder(google_url)
        if isinstance(result, dict) and result.get('status') and result.get('decoded_url'):
            return result['decoded_url']
    except:
        pass
    return google_url

def main():
    if not NEWS_DB_URL:
        print("Erreur: NEWS_DATABASE_URL non trouvée.")
        return

    try:
        conn = psycopg2.connect(NEWS_DB_URL)
        cur = conn.cursor()
        
        # Recherche des articles du 1er octobre 2025
        query = """
        SELECT title, link, source 
        FROM \"Article\" 
        WHERE \"publishedAt\" >= '2025-10-01 00:00:00' 
          AND \"publishedAt\" <= '2025-10-01 23:59:59'
        ORDER BY \"publishedAt\" ASC
        """
        cur.execute(query)
        articles = cur.fetchall()
        
        print(f"--- Articles du 01/10/2025 ({len(articles)} trouvés) ---\n")
        
        for i, (title, link, source) in enumerate(articles, 1):
            print(f"{i}. [{source}] {title}")
            real_url = decode_url(link)
            print(f"   Lien Réel : {real_url}")
            print("-" * 20)
            
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Erreur : {e}")

if __name__ == "__main__":
    main()
