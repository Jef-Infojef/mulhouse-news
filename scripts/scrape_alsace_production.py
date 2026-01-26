import os
import psycopg2
from bs4 import BeautifulSoup
import json
import re
import time
import random
from curl_cffi import requests

# URL pour configurer les secrets : https://github.com/Jef-Infojef/mulhouse-news/settings/secrets/actions

def load_config():
    db_url = os.environ.get("DATABASE_URL")
    cookies_raw = os.environ.get("ALSACE_COOKIES")
    return db_url, cookies_raw

def fetch_article_content(url, cookies_dict):
    try:
        # Pause aléatoire pour la discrétion
        time.sleep(random.uniform(1, 2.5))
        
        resp = requests.get(
            url, 
            cookies=cookies_dict,
            impersonate="chrome110",
            timeout=30,
            allow_redirects=True
        )
        
        if resp.status_code != 200:
            return None, True

        page_text = resp.text
        # Détection de la session (logique validée)
        is_connected = any(x in page_text for x in ["Se déconnecter", "Mon compte", "Mon profil", "suscriber", "premium", "Abonné"])
        
        soup = BeautifulSoup(page_text, 'html.parser')
        text_parts = []
        
        # 1. Chapô (souvent visible même sans abonnement)
        chapo = soup.find(class_='chapo') or soup.find(class_='article__chapo')
        if chapo: text_parts.append(chapo.get_text().strip())
        
        # 2. Corps (uniquement si connecté pour éviter le paywall/tronquage)
        if is_connected:
            for modal in soup.find_all(class_='GXCO_content'): modal.decompose()
            content_blocks = soup.find_all('div', class_='textComponent')
            for block in content_blocks:
                txt = block.get_text("\n", strip=True)
                if len(txt) > 10: text_parts.append(txt)
            
        # 3. Fallback Vidéo/LD+JSON
        if not text_parts or not is_connected:
            for script in soup.find_all('script', type='application/ld+json'):
                try:
                    raw_json = script.string.strip()
                    # Nettoyage des clés bizarres comme " @type"
                    raw_json = raw_json.replace('" @', '"@')
                    data = json.loads(raw_json)
                    items = data if isinstance(data, list) else [data]
                    for item in items:
                        if item.get('@type') in ['VideoObject', 'NewsArticle'] and item.get('description'):
                            desc = item['description'].strip()
                            if desc not in text_parts: text_parts.append(desc)
                except: pass

        if text_parts:
            return "\n\n".join(text_parts), is_connected
        return None, is_connected

    except Exception as e:
        print(f"   ❌ Erreur fetch: {e}")
        return None, True

def main():
    print("=== SCRAPER ALSACE PRODUCTION (GITHUB) ===")
    db_url, cookies_raw = load_config()
    if not db_url or not cookies_raw:
        print("❌ Configuration manquante (DATABASE_URL ou ALSACE_COOKIES)")
        return

    # Préparation des cookies (logique V5 validée)
    cookies_dict = {}
    clean = cookies_raw.strip().replace('"', '').replace("'", "")
    if ':' in clean: clean = clean.split(':', 1)[1].strip()
    
    cookies_dict = {
        ".XCONNECT_SESSION": clean,
        ".XCONNECTKeepAlive": "2=1",
        ".XCONNECT": "2=1",
        "_poool": "9aab6ee3-fda6-43fc-a90e-29de3c73d8f7"
    }

    try:
        url = db_url.replace("?pgbouncer=true", "")
        conn = psycopg2.connect(url)
        cur = conn.cursor()

        # On cible tout ce qui est vide en 2024 et 2025
        cur.execute("""
            SELECT id, title, link 
            FROM "Article" 
            WHERE source ILIKE '%Alsace%' 
              AND content IS NULL
              AND link LIKE '%www.lalsace.fr%'
              AND "publishedAt" >= '2024-01-01'
              AND "publishedAt" < '2026-01-01'
            ORDER BY "publishedAt" DESC
            LIMIT 300
        """)
        articles = cur.fetchall()
        
        if not articles:
            print("✨ Aucun article à scraper.")
            return

        print(f"[*] {len(articles)} articles à traiter dans cette session.")

        success_count = 0
        for i, (art_id, title, link) in enumerate(articles, 1):
            content, session_active = fetch_article_content(link, cookies_dict)
            
            if not session_active:
                print(f"[{i}/{len(articles)}] ⚠️ Session perdue ou non connectée | {title[:50]}...")
                # On ne break plus, on continue pour tenter de chopper ce qu'on peut sur les autres
            
            if content:
                try:
                    cur.execute('UPDATE "Article" SET content = %s WHERE id = %s', (content, art_id))
                    conn.commit()
                    print(f"[{i}/{len(articles)}] ✅ {len(content)} chars | {title[:50]}...")
                    success_count += 1
                except Exception as e:
                    print(f"[{i}/{len(articles)}] ❌ Erreur DB: {e}")
                    conn.rollback()
            else:
                print(f"[{i}/{len(articles)}] ⚠️ Vide ou Non Autorisé | {link}")

        print(f"\n[*] TERMINÉ. {success_count} articles mis à jour.")
        cur.close()
        conn.close()
    except Exception as e:
        print(f"❌ Erreur critique : {e}")

if __name__ == "__main__":
    main()
