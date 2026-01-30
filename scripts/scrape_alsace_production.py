import os
import psycopg2
from bs4 import BeautifulSoup
import json
import re
import time
import random
from curl_cffi import requests

# URL pour configurer les secrets : https://github.com/Jef-Infojef/mulhouse-news/settings/secrets/actions

def get_app_config(conn, key):
    try:
        cur = conn.cursor()
        cur.execute('SELECT value FROM "AppConfig" WHERE key = %s', (key,))
        row = cur.fetchone()
        return row[0] if row else None
    except:
        return None

def main():
    print("=== SCRAPER ALSACE PRODUCTION (GITHUB) ===")
    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        print("❌ Configuration manquante (DATABASE_URL)")
        return

    try:
        url = db_url.replace("?pgbouncer=true", "")
        conn = psycopg2.connect(url)
        
        # Priorité 1 : Base de données
        cookies_raw = get_app_config(conn, "EBRA_COOKIE")
        
        # Priorité 2 : Fallback Secret GitHub
        if not cookies_raw:
            cookies_raw = os.environ.get("ALSACE_COOKIES")
            if cookies_raw:
                print("[*] Utilisation du cookie fallback (Secret GitHub)")

        if not cookies_raw:
            print("❌ Aucun cookie trouvé (ni en base, ni en secret).")
            conn.close()
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
