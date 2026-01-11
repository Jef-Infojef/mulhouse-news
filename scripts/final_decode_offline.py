import base64
import re
import psycopg2
import os
from dotenv import load_dotenv

def decode_google_news_url(url):
    try:
        if "articles/" not in url: return url
        base64_str = url.split("articles/")[1].split("?")[0]
        
        padding = (4 - len(base64_str) % 4) % 4
        decoded_bytes = base64.urlsafe_b64decode(base64_str + "=" * padding)
        
        data = decoded_bytes
        start_idx = data.find(b"http")
        if start_idx == -1: return url
        
        end_idx = start_idx
        while end_idx < len(data) and 32 <= data[end_idx] < 127:
            end_idx += 1
            
        return data[start_idx:end_idx].decode('utf-8')
    except Exception:
        return url

load_dotenv(".env.local")
NEWS_DB_URL = os.environ.get("NEWS_DATABASE_URL")

def main():
    if not NEWS_DB_URL: 
        print("Erreur : NEWS_DATABASE_URL manquante")
        return
    conn = psycopg2.connect(NEWS_DB_URL)
    cur = conn.cursor()
    cur.execute("""
        SELECT title, link, source FROM "Article" 
        WHERE "publishedAt" >= '2025-10-01 00:00:00' 
          AND "publishedAt" <= '2025-10-01 23:59:59'
        ORDER BY "publishedAt" ASC
    """)
    articles = cur.fetchall()
    
    print("--- Articles du 01/10/2025 ---")
    for i, (title, link, source) in enumerate(articles, 1):
        real_url = decode_google_news_url(link)
        print(f"{i}. [{source}] {title}")
        print(f"   Lien : {real_url}")
        print("-" * 15)
        
    cur.close()
    conn.close()

if __name__ == "__main__":
    main()