import os
import psycopg2
from bs4 import BeautifulSoup
import json
import re
import time
import random
import subprocess
from curl_cffi import requests
from dotenv import load_dotenv
from datetime import datetime

# Charger l'environnement
load_dotenv(".envenv")
load_dotenv(".env.local")
load_dotenv(".env")

DATABASE_URL = os.environ.get("DATABASE_URL")
ALSACE_COOKIES = os.environ.get("ALSACE_COOKIES")

def get_db_connection():
    if not DATABASE_URL:
        raise ValueError("DATABASE_URL is not set")
    clean_url = DATABASE_URL.replace("?pgbouncer=true", "").replace("&pgbouncer=true", "")
    return psycopg2.connect(clean_url)

def fetch_article_content(url, cookies_dict):
    """Récupère le contenu complet selon la source."""
    try:
        time.sleep(random.uniform(1.0, 2.0))
        resp = requests.get(url, cookies=cookies_dict, impersonate="chrome110", timeout=30, allow_redirects=True)
        if resp.status_code != 200:
            return None, True, f"HTTP {resp.status_code}"

        page_text = resp.text
        is_connected = any(x in page_text for x in ["Se déconnecter", "Mon compte", "Mon profil", "suscriber", "premium"])
        if not is_connected and ALSACE_COOKIES and "lalsace.fr" in url:
            return None, False, "Session lost"

        soup = BeautifulSoup(page_text, 'html.parser')
        text_parts = []

        # Logique EBRA (L'Alsace, DNA...)
        if any(x in url for x in ["lalsace.fr", "dna.fr", "estrepublicain.fr"]):
            chapo = soup.find(class_='chapo') or soup.find(class_='article__chapo')
            if chapo: text_parts.append(chapo.get_text().strip())
            for block in soup.find_all('div', class_='textComponent'):
                txt = block.get_text("\n", strip=True)
                if len(txt) > 10: text_parts.append(txt)
            if not text_parts:
                for script in soup.find_all('script', type='application/ld+json'):
                    try:
                        data = json.loads(script.string)
                        items = data if isinstance(data, list) else [data]
                        for item in items:
                            if item.get('@type') in ['VideoObject', 'NewsArticle'] and item.get('description'):
                                text_parts.append(item['description'].strip())
                    except: pass
        # Logique Le Parisien
        elif "leparisien.fr" in url:
            for script in soup.find_all('script', type='application/ld+json'):
                try:
                    data = json.loads(script.string.strip())
                    item = data[0] if isinstance(data, list) else data
                    if item.get('@type') == 'NewsArticle' and 'articleBody' in item:
                        return item['articleBody'], True, None
                except: pass
        # Fallback générique
        if not text_parts:
            body = soup.find('div', itemprop='articleBody') or soup.find('article')
            if body:
                text_parts.extend([p.get_text().strip() for p in body.find_all('p') if len(p.get_text().strip()) > 40])

        if text_parts:
            return "\n\n".join(dict.fromkeys(text_parts)), True, None # déduplication simple
        return None, True, "No content found"
    except Exception as e:
        return None, True, str(e)

def run_image_scripts():
    """Lance les scripts TS et retourne un résumé."""
    print("\n[*] Traitement des images et B2...")
    try:
        # Utilisation de tsx (plus robuste sur GitHub Actions/ESM)
        subprocess.run(["npx", "tsx", "scripts/download_images.ts"], check=True)
        subprocess.run(["npx", "tsx", "scripts/sync_to_b2.ts"], check=True)
        return "Success"
    except Exception as e:
        return f"Error: {str(e)}"

def main():
    start_time = datetime.now()
    print(f"=== SCRAPER PRODUCTION V2 (WITH LOGS) - {start_time.strftime('%H:%M:%S')} ===")
    
    cookies_dict = {}
    if ALSACE_COOKIES:
        clean = ALSACE_COOKIES.strip().replace('"', '').replace("'", "")
        if ':' in clean: clean = clean.split(':', 1)[1].strip()
        cookies_dict = {".XCONNECT_SESSION": clean, ".XCONNECTKeepAlive": "2=1", ".XCONNECT": "2=1", "_poool": "9aab6ee3-fda6-43fc-a90e-29de3c73d8f7"}

    conn = None
    session_details = []
    stats = {"success": 0, "error": 0, "is_connected": False}

    try:
        conn = get_db_connection()
        cur = conn.cursor()

        # Vérification connexion initiale
        test_resp = requests.get("https://www.lalsace.fr/", cookies=cookies_dict, impersonate="chrome110", timeout=15)
        stats["is_connected"] = any(x in test_resp.text for x in ["Se déconnecter", "Mon compte"])
        print(f"[*] État initial connexion : {'✅' if stats['is_connected'] else '❌'}")

        cur.execute("""
            SELECT id, title, link 
            FROM \"Article\" 
            WHERE (content IS NULL OR LENGTH(content) < 150)
              AND \"publishedAt\" > NOW() - INTERVAL '7 days'
            ORDER BY \"publishedAt\" DESC LIMIT 50
        """)
        articles = cur.fetchall()
        
        for i, (art_id, title, link) in enumerate(articles, 1):
            # Si on n'est pas connecté, on saute les sites qui nécessitent un compte
            is_ebra = any(x in link for x in ["lalsace.fr", "dna.fr", "estrepublicain.fr"])
            if is_ebra and not stats["is_connected"]:
                print(f"    [{i}/{len(articles)}] SKIP | {title[:40]}... (Non connecté)")
                session_details.append({"title": title, "link": link, "status": "SKIPPED", "error": "Not connected"})
                continue

            content, active, err = fetch_article_content(link, cookies_dict)
            status = "SUCCESS" if content else "FAILED"
            if not active:
                status = "SESSION_LOST"
                session_details.append({"title": title, "link": link, "status": status, "error": err})
                print(f"🛑 Session perdue à l'article {i}")
                break
            
            if content:
                cur.execute('UPDATE "Article" SET content = %s WHERE id = %s', (content, art_id))
                conn.commit()
                stats["success"] += 1
            else:
                stats["error"] += 1
            
            session_details.append({"title": title, "link": link, "status": status, "error": err, "chars": len(content) if content else 0})
            print(f"    [{i}/{len(articles)}] {status} | {title[:40]}...")

        # Image processing
        img_status = run_image_scripts()
        
        # Enregistrement du LOG final
        finished_at = datetime.now()
        status_final = "SUCCESS" if stats["error"] == 0 else "PARTIAL"
        if any(d["status"] == "SESSION_LOST" for d in session_details): status_final = "SESSION_LOST"

        cur.execute("""
            INSERT INTO "ScrapingLog" (id, "startedAt", "finishedAt", status, "isConnected", "articlesCount", "successCount", "errorCount", details)
            VALUES (gen_random_uuid(), %s, %s, %s, %s, %s, %s, %s, %s)
        """, (start_time, finished_at, status_final, stats["is_connected"], len(articles), stats["success"], stats["error"], json.dumps(session_details)))
        conn.commit()
        print(f"\n✅ Log enregistré en base de données. Statut: {status_final}")

    except Exception as e:
        print(f"❌ Erreur critique : {e}")
        if conn:
            try:
                cur = conn.cursor()
                cur.execute("""
                    INSERT INTO "ScrapingLog" (id, "startedAt", "finishedAt", status, "errorMessage")
                    VALUES (gen_random_uuid(), %s, NOW(), 'FAILED', %s)
                """, (start_time, str(e)))
                conn.commit()
            except: pass
    finally:
        if conn: conn.close()

if __name__ == "__main__":
    main()
