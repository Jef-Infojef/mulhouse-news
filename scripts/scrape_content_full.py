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

def get_db_connection():
    if not DATABASE_URL:
        raise ValueError("DATABASE_URL is not set")
    clean_url = DATABASE_URL.replace("?pgbouncer=true", "").replace("&pgbouncer=true", "")
    return psycopg2.connect(clean_url)

def get_app_config(conn, key):
    try:
        with conn.cursor() as cur:
            cur.execute('SELECT value FROM "AppConfig" WHERE key = %s', (key,))
            row = cur.fetchone()
            return row[0] if row else None
    except:
        return None

def fetch_article_content(url, cookies_dict, alsace_cookies_active):
    """Récupère le contenu complet selon la source."""
    try:
        # Fallback intelligent pour le groupe EBRA (DNA, Est Républicain, etc.)
        # Si on a des cookies L'Alsace, on tente de transformer l'URL DNA/EstRep en L'Alsace
        target_url = url
        if alsace_cookies_active and ("dna.fr" in url or "estrepublicain.fr" in url or "vosgesmatin.fr" in url):
            target_url = url.replace("www.dna.fr", "www.lalsace.fr").replace("www.estrepublicain.fr", "www.lalsace.fr").replace("www.vosgesmatin.fr", "www.lalsace.fr")
            if target_url != url:
                print(f"    [🔄] Test Fallback L'Alsace pour : {url[:40]}...")

        time.sleep(random.uniform(1.0, 2.0))
        
        try:
            resp = requests.get(target_url, cookies=cookies_dict, impersonate="chrome110", timeout=30, allow_redirects=True)
        except Exception as ssl_err:
            if "CertificateVerifyError" in str(ssl_err) or "SSL" in str(ssl_err):
                resp = requests.get(target_url, cookies=cookies_dict, impersonate="chrome110", timeout=30, allow_redirects=True, verify=False)
            else:
                raise ssl_err
        
        # Si le fallback L'Alsace échoue (404), on tente l'URL originale sans cookies (pour les gratuits)
        if resp.status_code == 404 and target_url != url:
            try:
                resp = requests.get(url, impersonate="chrome110", timeout=20, allow_redirects=True)
            except Exception as ssl_err:
                if "CertificateVerifyError" in str(ssl_err) or "SSL" in str(ssl_err):
                    resp = requests.get(url, impersonate="chrome110", timeout=20, allow_redirects=True, verify=False)
                else:
                    raise ssl_err
            
        if resp.status_code != 200:
            return None, True, f"HTTP {resp.status_code}"

        page_text = resp.text
        is_connected = any(x in page_text for x in ["Se déconnecter", "Mon compte", "Mon profil", "suscriber", "premium", "Abonné"])
        
        # Si c'était un article L'Alsace (ou transformé en L'Alsace) et qu'on n'est pas connecté
        if not is_connected and alsace_cookies_active and "lalsace.fr" in target_url:
            # On continue quand même pour tenter de choper le chapo ou LD+JSON
            print(f"    [!] Mode non-abonné pour : {target_url[:40]}")

        soup = BeautifulSoup(page_text, 'html.parser')
        text_parts = []

        # Logique EBRA (L'Alsace, DNA...)
        if any(x in target_url for x in ["lalsace.fr", "dna.fr", "estrepublicain.fr"]):
            # ... [Logique EBRA existante conservée] ...
            if "lalsace.fr" in target_url and not is_connected:
                print(f"    [⛔] Contenu partiel refusé (Non connecté) pour : {target_url[:40]}")
                return None, False, "Not Connected (Partial content refused)"

            chapo = soup.find(class_='chapo') or soup.find(class_='article__chapo')
            if chapo: text_parts.append(chapo.get_text().strip())
            
            inner = soup.find(class_='innerContent')
            if inner: text_parts.append(inner.get_text(strip=True))

            if is_connected:
                for block in soup.find_all('div', class_='textComponent'):
                    txt = block.get_text("\n", strip=True)
                    if len(txt) > 10: text_parts.append(txt)
            
            if not text_parts or len("\n".join(text_parts)) < 100:
                for script in soup.find_all('script', type='application/ld+json'):
                    try:
                        raw_json = script.string.strip()
                        raw_json = raw_json.replace('" @', '"@')
                        data = json.loads(raw_json)
                        items = data if isinstance(data, list) else [data]
                        for item in items:
                            if item.get('@type') in ['VideoObject', 'NewsArticle'] and item.get('description'):
                                text_parts.append(item['description'].strip())
                    except: pass
        # Logique JDS (Agenda)
        elif "jds.fr" in url:
            desc_div = soup.find('div', class_='description') or soup.find('div', id='description') or soup.find('div', itemprop='description')
            if desc_div:
                text_parts.append(desc_div.get_text(separator="\n", strip=True))
        # Logique Le Parisien
        elif "leparisien.fr" in url:
            for script in soup.find_all('script', type='application/ld+json'):
                try:
                    data = json.loads(script.string.strip())
                    item = data[0] if isinstance(data, list) else data
                    if item.get('@type') == 'NewsArticle' and 'articleBody' in item:
                        return item['articleBody'], True, None
                except: pass
        # Logique M+ (Mulhouse Alsace Agglomération)
        elif "mag.mulhouse-alsace.fr" in url:
            content_div = soup.find('div', class_='interne')
            if content_div:
                text_parts.append(content_div.get_text(separator="\n\n", strip=True))
        # Fallback générique
        if not text_parts:
            body = soup.find('div', itemprop='articleBody') or soup.find('article')
            if body:
                text_parts.extend([p.get_text().strip() for p in body.find_all('p') if len(p.get_text().strip()) > 40])

        if text_parts:
            # Nettoyage des caractères NULL (PostgreSQL n'aime pas ça)
            clean_parts = [p.replace('\x00', '') for p in text_parts if p]
            return "\n\n".join(dict.fromkeys(clean_parts)), True, None # déduplication simple
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
    
    conn = None
    session_details = []
    stats = {"success": 0, "error": 0, "is_connected": False}

    try:
        conn = get_db_connection()
        
        # Récupération des nouveaux champs séparés (Priorité 1)
        db_session = get_app_config(conn, "EBRA_SESSION")
        db_poool = get_app_config(conn, "EBRA_POOOL")
        
        alsace_cookies = None
        cookies_dict = {}

        if db_session:
            # Nettoyage session
            s_val = db_session.strip().replace('"', '').replace("'", "")
            if "2=" in s_val:
                s_val = s_val[s_val.find("2="):].split(";")[0]
            
            # Nettoyage poool
            p_val = db_poool.strip().replace('"', '').replace("'", "") if db_poool else "9aab6ee3-fda6-43fc-a90e-29de3c73d8f7"
            if "_poool=" in p_val:
                p_val = p_val.split("_poool=")[1].split(";")[0]
            
            cookies_dict = {
                ".XCONNECT_SESSION": s_val,
                ".XCONNECTKeepAlive": "2=1",
                ".XCONNECT": "2=1",
                "_poool": p_val
            }
            alsace_cookies = "DB_ACTIVE"
            print(f"[*] Session active via DB (Poool: {p_val[:8]}...)")

        # Fallback sur l'ancien champ EBRA_COOKIE ou Secret GitHub (Priorité 2)
        if not alsace_cookies:
            fallback = get_app_config(conn, "EBRA_COOKIE") or os.environ.get("ALSACE_COOKIES")
            if fallback:
                print("[*] Utilisation du cookie fallback")
                clean = fallback.strip().replace('"', '').replace("'", "")
                if ";" in clean and "=" in clean:
                    for item in clean.split(";"):
                        if "=" in item:
                            k, v = item.split("=", 1)
                            cookies_dict[k.strip()] = v.strip()
                else:
                    session_val = clean[clean.find("2="):].split(";")[0] if "2=" in clean else clean
                    cookies_dict = {".XCONNECT_SESSION": session_val, ".XCONNECTKeepAlive": "2=1", ".XCONNECT": "2=1", "_poool": "9aab6ee3-fda6-43fc-a90e-29de3c73d8f7"}
                alsace_cookies = "FALLBACK_ACTIVE"

        cur = conn.cursor()

        # Vérification connexion initiale
        try:
            test_resp = requests.get("https://www.lalsace.fr/", cookies=cookies_dict, impersonate="chrome110", timeout=15)
            stats["is_connected"] = any(x in test_resp.text for x in ["Se déconnecter", "Mon compte"])
        except:
            stats["is_connected"] = False
            
        print(f"[*] État initial connexion : {'✅' if stats['is_connected'] else '❌'}")

        cur.execute("""
            SELECT id, title, link 
            FROM "Article" 
            WHERE (content IS NULL OR LENGTH(content) < 150)
              AND "publishedAt" > NOW() - INTERVAL '24 hours'
            ORDER BY "publishedAt" DESC LIMIT 50
        """)
        articles = cur.fetchall()
        
        for i, (art_id, title, link) in enumerate(articles, 1):
            # On récupère la description actuelle pour le fallback
            cur.execute('SELECT description FROM "Article" WHERE id = %s', (art_id,))
            row_desc = cur.fetchone()
            current_desc = row_desc[0] if row_desc else None

            # Tentative d'extraction du contenu complet
            content, active, err = fetch_article_content(link, cookies_dict, alsace_cookies is not None)
            
            status = "SUCCESS" if content else "FAILED"
            
            # Si l'extraction échoue, on utilise la description comme contenu de secours
            final_content = content
            if not final_content and current_desc:
                final_content = current_desc
                status = "FALLBACK"
                print(f"    [💡] Utilisation de la description pour : {title[:40]}...")
            
            # On ne break plus si la session est perdue, on continue pour les autres
            if not active:
                status = "SESSION_LOST"
            
            if final_content:
                cur.execute('UPDATE "Article" SET content = %s WHERE id = %s', (final_content, art_id))
                conn.commit()
                if status != "FALLBACK": stats["success"] += 1
            else:
                stats["error"] += 1
            
            session_details.append({"title": title, "link": link, "status": status, "error": err, "chars": len(final_content) if final_content else 0})
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
