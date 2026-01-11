import os
import psycopg2
import requests
import re
from dotenv import load_dotenv

load_dotenv(".env.local")
NEWS_DB_URL = os.environ.get("NEWS_DATABASE_URL")

def get_real_url_with_consent(google_url):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
        'Accept-Language': 'fr-FR,fr;q=0.9,en-US;q=0.8,en;q=0.7',
        'Referer': 'https://news.google.com/',
        'DNT': '1',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1'
    }
    
    session = requests.Session()
    try:
        # Première requête pour choper les cookies de consentement si besoin
        resp = session.get(google_url, headers=headers, timeout=15, allow_redirects=True)
        
        # Si on est sur une page de consentement, on essaie d'extraire l'URL de destination
        if "consent.google.com" in resp.url:
            match = re.search(r'continue=([^&]+)', resp.url)
            if match:
                import urllib.parse
                dest_url = urllib.parse.unquote(match.group(1))
                # On réessaie sur la destination
                resp = session.get(dest_url, headers=headers, timeout=15, allow_redirects=True)
        
        # On regarde si l'URL finale n'est plus chez google
        if "google.com" not in resp.url or "news.google.com/rss/articles" not in resp.url:
            return resp.url

        # Si toujours bloqué, on cherche dans le texte de la page
        # Parfois le lien est dans un <a href="..."> ou une redirection JS
        real_url_match = re.search(r'window\.location\.replace\("([^"]+)"\)', resp.text)
        if real_url_match:
            return real_url_match.group(1)
            
        # Chercher un lien vers l'article original dans le corps de la page
        # Souvent Google affiche "You are being redirected to..."
        return resp.url
    except Exception as e:
        return f"Erreur : {e}"

def main():
    if not NEWS_DB_URL: return
    conn = psycopg2.connect(NEWS_DB_URL)
    cur = conn.cursor()
    cur.execute("""
        SELECT title, link, source FROM "Article" 
        WHERE "publishedAt" >= '2025-10-01 00:00:00' 
          AND "publishedAt" <= '2025-10-01 23:59:59'
        ORDER BY "publishedAt" ASC
    """)
    articles = cur.fetchall()
    
    for i, (title, link, source) in enumerate(articles, 1):
        print(f"{i}. {title}")
        # On ne traite que si c'est un lien google
        if "news.google.com" in link:
            real = get_real_url_with_consent(link)
            print(f"   Lien : {real}")
        else:
            print(f"   Lien : {link}")
        print("-" * 10)
    
    cur.close()
    conn.close()

if __name__ == "__main__":
    main()
