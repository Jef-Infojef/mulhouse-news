import os
import psycopg2
from curl_cffi import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
import time
import random
import json

# Configuration
load_dotenv(".env.local")
DATABASE_URL = os.environ.get("DATABASE_URL")
ALSACE_COOKIES_RAW = os.environ.get("ALSACE_COOKIES")

def get_db_connection():
    if not DATABASE_URL:
        raise ValueError("DATABASE_URL is not set")
    # GitHub Actions injecte DATABASE_URL sans forcément nettoyer pgbouncer
    clean_url = DATABASE_URL.replace("?pgbouncer=true", "").replace("&pgbouncer=true", "")
    return psycopg2.connect(clean_url)

def fetch_generic_content(url):
    """Tente de récupérer le contenu de manière générique ou spécifique selon la source."""
    try:
        # Délai aléatoire pour éviter d'être banni
        time.sleep(random.uniform(1.0, 3.0))
        
        # Préparation des cookies si disponibles
        cookies = {}
        if ALSACE_COOKIES_RAW and ("lalsace.fr" in url or "dna.fr" in url):
            for part in ALSACE_COOKIES_RAW.split(';'):
                if '=' in part:
                    key, value = part.strip().split('=', 1)
                    cookies[key] = value

        response = requests.get(url, impersonate="chrome120", timeout=20, cookies=cookies)
        if response.status_code != 200:
            return None

        soup = BeautifulSoup(response.text, 'html.parser')
        
        # --- LOGIQUE SPÉCIFIQUE : LE PARISIEN ---
        if "leparisien.fr" in url:
            scripts = soup.find_all('script', type='application/ld+json')
            for script in scripts:
                try:
                    data = json.loads(script.string.strip())
                    if isinstance(data, list): data = data[0]
                    if data.get('@type') == 'NewsArticle' and 'articleBody' in data:
                        return data['articleBody']
                except: continue

        # --- LOGIQUE SPÉCIFIQUE : L'ALSACE / EBRA ---
        if "lalsace.fr" in url or "dna.fr" in url:
            text_parts = []
            chapo = soup.find(class_='chapo') or soup.find(class_='article__chapo')
            if chapo: text_parts.append(chapo.get_text().strip())
            
            main_article = soup.find('div', class_='col_main') or soup.find('article')
            if main_article:
                all_text_divs = main_article.find_all('div', class_='textComponent')
                if not all_text_divs:
                    fallback = main_article.find('div', class_='c-article-content') or main_article.find('div', itemprop='articleBody')
                    if fallback: all_text_divs = [fallback]
                
                for div in all_text_divs:
                    for garbage in div.select('.c-read-also, .gl-ad, script, style, .paywall'):
                        garbage.decompose()
                    text_parts.extend([p.get_text().strip() for p in div.find_all('p') if p.get_text().strip()])
            
            if text_parts: return "\n\n".join(text_parts)

        # --- LOGIQUE GÉNÉRIQUE (Fallback) ---
        # On cherche des balises communes pour le contenu
        article_body = soup.find('div', itemprop='articleBody') or \
                       soup.find('article') or \
                       soup.find('div', class_='article-content')
        
        if article_body:
            paragraphs = [p.get_text().strip() for p in article_body.find_all('p') if len(p.get_text().strip()) > 40]
            if paragraphs:
                return "\n\n".join(paragraphs)

        return None

    except Exception as e:
        print(f"      [!] Erreur fetch ({url}): {e}")
        return None

def main():
    print("[*] Démarrage du récupérateur de contenu complet...")
    
    try:
        conn = get_db_connection()
        cur = conn.cursor()
    except Exception as e:
        print(f"[!] Erreur connexion DB: {e}")
        return

    # On récupère les 30 derniers articles sans contenu
    # On limite pour ne pas faire durer le job GitHub Action trop longtemps
    cur.execute("""
        SELECT id, title, link 
        FROM \"Article\" 
        WHERE (content IS NULL OR LENGTH(content) < 200)
          AND (link LIKE '%lalsace.fr%' OR link LIKE '%leparisien.fr%' OR link LIKE '%dna.fr%')
        ORDER BY \"publishedAt\" DESC
        LIMIT 30
    """)
    articles = cur.fetchall()
    
    if not articles:
        print("[*] Aucun article en attente de contenu.")
        return

    print(f"[*] Traitement de {len(articles)} articles...")

    success_count = 0
    for i, (art_id, title, link) in enumerate(articles, 1):
        print(f"    [{i}/{len(articles)}] {title[:60]}...")
        
        content = fetch_generic_content(link)
        
        if content and len(content) > 200:
            try:
                cur.execute('UPDATE \"Article\" SET content = %s WHERE id = %s', (content, art_id))
                conn.commit()
                success_count += 1
                print(f"      -> ✅ Contenu ajouté ({len(content)} chars)")
            except Exception as e:
                print(f"      -> ❌ Erreur BDD: {e}")
                conn.rollback()
        else:
            print(f"      -> ⚠️ Contenu non trouvé ou trop court")

    cur.close()
    conn.close()
    print(f"[*] Terminé. {success_count} articles enrichis.")

if __name__ == "__main__":
    main()
