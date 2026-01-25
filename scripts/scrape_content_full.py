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
    """Récupère le contenu complet selon la source avec logiques spécifiques."""
    try:
        # Pause aléatoire pour la discrétion
        time.sleep(random.uniform(1.0, 2.0))
        
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
        soup = BeautifulSoup(page_text, 'html.parser')
        text_parts = []

        # --- 1. L'ALSACE / DNA / EST REPUBLICAIN (EBRA) ---
        if any(x in url for x in ["lalsace.fr", "dna.fr", "estrepublicain.fr"]):
            is_connected = any(x in page_text for x in ["Se déconnecter", "Mon compte", "Mon profil", "suscriber", "premium"])
            if not is_connected and ALSACE_COOKIES:
                return None, False # Session perdue

            chapo = soup.find(class_='chapo') or soup.find(class_='article__chapo')
            if chapo: text_parts.append(chapo.get_text().strip())
            
            content_blocks = soup.find_all('div', class_='textComponent')
            for block in content_blocks:
                txt = block.get_text("\n", strip=True)
                if len(txt) > 10: text_parts.append(txt)
            
            if not text_parts:
                # Fallback Vidéo LD+JSON
                for script in soup.find_all('script', type='application/ld+json'):
                    try:
                        data = json.loads(script.string)
                        items = data if isinstance(data, list) else [data]
                        for item in items:
                            if item.get('@type') in ['VideoObject', 'NewsArticle'] and item.get('description'):
                                text_parts.append(item['description'].strip())
                    except: pass

        # --- 2. MPLUS (MULHOUSE ALSACE MAG) ---
        elif "mag.mulhouse-alsace.fr" in url:
            extrait = soup.find('p', class_='extrait')
            if extrait: text_parts.append(extrait.get_text().strip())
            
            content_div = soup.find('div', class_='interne') or \
                          soup.find('div', class_='tribe-events-single-event-description') or \
                          soup.find('div', class_='entry-content')
            if content_div:
                for garbage in content_div.select('.important, .encadre, script, style, .sharedaddy'): 
                    garbage.decompose()
                text_parts.append(content_div.get_text("\n", strip=True))

        # --- 3. FRANCE 3 / FRANCE INFO ---
        elif "france3-regions" in url or "franceinfo.fr" in url:
            intro = soup.find('p', class_='article__intro')
            if intro: text_parts.append(intro.get_text().strip())
            
            body = soup.find('div', class_='article__body') or soup.find('div', class_='entry-content')
            if body:
                for element in body.find_all(['p', 'h2']):
                    txt = element.get_text().strip()
                    if len(txt) > 10: text_parts.append(txt)

        # --- 4. ACTU.FR ---
        elif "actu.fr" in url:
            main_header = soup.find('div', class_='ac-article-main')
            if main_header and main_header.find('p'):
                text_parts.append(main_header.find('p').get_text().strip())
            
            content_div = soup.find('div', class_='ac-article-content')
            if content_div:
                for element in content_div.find_all(['p', 'h2']):
                    txt = element.get_text().strip()
                    if len(txt) > 10 and "Mon Actu" not in txt:
                        text_parts.append(txt)

        # --- 5. FRANCE BLEU ---
        elif "francebleu.fr" in url:
            standfirst = soup.find('p', class_='standfirst')
            if standfirst: text_parts.append(standfirst.get_text().strip())
            
            body_div = soup.find('div', class_='IciBody')
            if body_div:
                for p in body_div.find_all('p'):
                    txt = p.get_text().strip()
                    if len(txt) > 10 and "publicité" not in txt:
                        text_parts.append(txt)

        # --- 6. LE PARISIEN ---
        elif "leparisien.fr" in url:
            for script in soup.find_all('script', type='application/ld+json'):
                try:
                    data = json.loads(script.string.strip())
                    item = data[0] if isinstance(data, list) else data
                    if item.get('@type') == 'NewsArticle' and 'articleBody' in item:
                        text_parts.append(item['articleBody'])
                except: pass

        # --- 7. FALLBACK GÉNÉRIQUE ---
        if not text_parts:
            article_body = soup.find('div', itemprop='articleBody') or \
                           soup.find('article') or \
                           soup.find('div', class_='article-content')
            if article_body:
                for garbage in article_body.select('script, style, .ads'): garbage.decompose()
                paragraphs = [p.get_text().strip() for p in article_body.find_all('p') if len(p.get_text().strip()) > 40]
                text_parts.extend(paragraphs)

        if text_parts:
            # Déduplication simple et nettoyage
            unique_parts = []
            for p in text_parts:
                if p not in unique_parts: unique_parts.append(p)
            return "\n\n".join(unique_parts), True
            
        return None, True

    except Exception as e:
        print(f"      ❌ Erreur fetch ({url}): {e}")
        return None, True

def run_image_scripts():
    """Lance les scripts TS pour les images et B2."""
    print("\n[*] Traitement des images et synchronisation B2...")
    try:
        # Téléchargement des images
        subprocess.run(["npx", "ts-node", "scripts/download_images.ts"], check=True)
        # Synchronisation B2
        subprocess.run(["npx", "ts-node", "scripts/sync_to_b2.ts"], check=True)
        print("   ✅ Images et B2 OK.")
    except Exception as e:
        print(f"   ❌ Erreur lors du traitement des images: {e}")

def main():
    print("=== SCRAPER DE PRODUCTION (CONTENU + IMAGES) ===")
    
    # Préparation des cookies
    cookies_dict = {}
    if ALSACE_COOKIES:
        clean = ALSACE_COOKIES.strip().replace('"', '').replace("'", "")
        if ':' in clean: clean = clean.split(':', 1)[1].strip()
        cookies_dict = {".XCONNECT_SESSION": clean, ".XCONNECTKeepAlive": "2=1", ".XCONNECT": "2=1", "_poool": "9aab6ee3-fda6-43fc-a90e-29de3c73d8f7"}

    try:
        conn = get_db_connection()
        cur = conn.cursor()

        # On cible les articles sans contenu des 7 derniers jours (toutes sources)
        cur.execute("""
            SELECT id, title, link 
            FROM \"Article\" 
            WHERE (content IS NULL OR LENGTH(content) < 150)
              AND \"publishedAt\" > NOW() - INTERVAL '7 days'
            ORDER BY \"publishedAt\" DESC
            LIMIT 50
        """)
        articles = cur.fetchall()
        
        if not articles:
            print("✨ Aucun article à enrichir.")
        else:
            print(f"[*] {len(articles)} articles à traiter.")
            success_count = 0
            for i, (art_id, title, link) in enumerate(articles, 1):
                content, session_active = fetch_article_content(link, cookies_dict)
                
                if not session_active:
                    print(f"\n🛑 ARRÊT : Session perdue à l'article {i}.")
                    break

                if content:
                    try:
                        cur.execute('UPDATE \"Article\" SET content = %s WHERE id = %s', (content, art_id))
                        conn.commit()
                        print(f"    [{i}/{len(articles)}] ✅ {len(content)} chars | {title[:50]}...")
                        success_count += 1
                    except Exception as e:
                        print(f"    [{i}/{len(articles)}] ❌ Erreur DB: {e}")
                        conn.rollback()
                else:
                    print(f"    [{i}/{len(articles)}] ⚠️ Vide | {link}")

            print(f"\n[*] Enrichissement terminé. {success_count} articles mis à jour.")

        cur.close()
        conn.close()
        
        # Phase 2 : Images et B2
        run_image_scripts()

    except Exception as e:
        print(f"❌ Erreur critique : {e}")

if __name__ == "__main__":
    main()