import os
import psycopg2
import requests
from googlenewsdecoder import gnewsdecoder
from dotenv import load_dotenv

load_dotenv(".env.local")

NEWS_DB_URL = os.environ.get("NEWS_DATABASE_URL")

def get_real_url(google_url):
    # Tentative avec le décodeur d'abord
    try:
        result = gnewsdecoder(google_url)
        if isinstance(result, dict) and result.get('status') and result.get('decoded_url'):
            decoded = result['decoded_url']
            if decoded != google_url:
                return decoded
    except:
        pass
    
    # Si le décodeur échoue, on suit la redirection
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(google_url, allow_redirects=True, timeout=10, headers=headers)
        return response.url
    except Exception as e:
        return f"Erreur de redirection : {e}"

def main():
    if not NEWS_DB_URL:
        print("Erreur: NEWS_DATABASE_URL non trouvée.")
        return

    try:
        conn = psycopg2.connect(NEWS_DB_URL)
        cur = conn.cursor()
        
        query = """
        SELECT title, link, source 
        FROM "Article" 
        WHERE "publishedAt" >= '2025-10-01 00:00:00' 
          AND "publishedAt" <= '2025-10-01 23:59:59'
        ORDER BY "publishedAt" ASC
        """
        cur.execute(query)
        articles = cur.fetchall()
        
        print(f"--- Articles du 01/10/2025 ({len(articles)} trouvés) ---\n")
        
        for i, (title, link, source) in enumerate(articles, 1):
            print(f"{i}. [{source}] {title}")
            real_url = get_real_url(link)
            print(f"   Lien Réel : {real_url}")
            print("-" * 20)
            
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Erreur : {e}")

if __name__ == "__main__":
    main()
