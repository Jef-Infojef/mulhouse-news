import os
import requests
import psycopg2
from bs4 import BeautifulSoup
from dotenv import load_dotenv
import time
import random

# Configuration
def load_env():
    # Try multiple possible env files in the root directory (one level up from scripts/)
    root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    env_files = [".envenv", ".env.local", ".env"]
    found = False
    for f in env_files:
        path = os.path.join(root_dir, f)
        if os.path.exists(path):
            load_dotenv(path)
            # If we found DATABASE_URL, we're good
            if os.environ.get("DATABASE_URL"):
                print(f"[*] Loaded configuration from {f}")
                found = True
                break
    
    if not found:
        # Fallback to current behavior if nothing found in root
        load_dotenv(".env.local")
        load_dotenv(".env")

load_env()
DATABASE_URL = os.environ.get("DATABASE_URL")

# Le cookie fourni par l'utilisateur
COOKIES_RAW = ".XCONNECT_SESSION=2=42F647DB9B788CF4E0AFFF1DD52DE98DD4096A6F311233168392F0CB5CC622941ABC8A02B31CCE14DC40C29F2CC31AC993FD6F18C904113908C0ADD6ED205E4D70BAB78120E53817EA8A3601C56DA10EC2E4CC18CA3D3DABC8010D8F6D19238B448B868308F1C005CA5F72156D3E8A0E1BFC7932E26560EC0BC9CA624672A4EB82F78EA4FE80A3CC067FC14156B9018CA2FC5920AAF5B7E197D47A0D0861225E435E340F78911F645826843278D0F48619E9D34FD36B530A61E50FDD833567F27D473AF7AE2066390855CBCB9A5073F29468B9D6C77CFACF67E48610218D5BBE38B4D706EB96D14CDFB3D0C28C153360; .XCONNECTKeepAlive=2=1; .XCONNECT=2=1; _poool=9aab6ee3-fda6-43fc-a90e-29de3c73d8f7; domain=lalsace.fr; path=/; secure; HttpOnly; SameSite=Lax"

# Parsing du cookie brut pour requests
cookies = {}
for part in COOKIES_RAW.split(';'):
    if '=' in part:
        key, value = part.strip().split('=', 1)
        cookies[key] = value

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
    'Accept-Language': 'fr-FR,fr;q=0.9',
    'Referer': 'https://www.lalsace.fr/',
}

def get_db_connection():
    # Nettoyage de l'URL pour psycopg2 (suppression du paramètre pgbouncer non supporté)
    url = DATABASE_URL
    if url and "?pgbouncer=true" in url:
        url = url.replace("?pgbouncer=true", "")
    return psycopg2.connect(url)

def fetch_article_content(session, url):
    try:
        time.sleep(random.uniform(0.5, 1.5)) # Pause polie
        response = session.get(url, timeout=15)
        
        if response.status_code != 200:
            print(f"   ⚠️ Status {response.status_code}")
            return None, True 

        # Vérification de la connexion sur la page
        is_still_connected = "Se déconnecter" in response.text or "mon compte" in response.text.lower()
        if not is_still_connected:
            return None, False

        soup = BeautifulSoup(response.text, 'html.parser')
        text_parts = []
        
        # 1. Le Chapô
        chapo = soup.find(class_='chapo') or soup.find(class_='article__chapo')
        if chapo:
            text_parts.append(chapo.get_text().strip())

        # 2. Le corps de l'article (textComponent)
        for modal in soup.find_all(class_='GXCO_content'):
            modal.decompose()
            
        content_blocks = soup.find_all('div', class_='textComponent')
        if content_blocks:
            for block in content_blocks:
                block_text = block.get_text("\n", strip=True)
                if block_text and len(block_text) > 10:
                    text_parts.append(block_text)
        
        # 3. Fallback LD+JSON (vidéos)
        if not text_parts:
            import json
            for script in soup.find_all('script', type='application/ld+json'):
                try:
                    data = json.loads(script.string)
                    items = data if isinstance(data, list) else [data]
                    for item in items:
                        if item.get('@type') == 'VideoObject' and item.get('description'):
                            text_parts.append(item['description'])
                            break
                    if text_parts: break
                except: pass

        # 4. Fallback structure EBRA classique
        if not text_parts:
            content_div = soup.find('div', class_='c-article-content') or \
                          soup.find('div', itemprop='articleBody') or \
                          soup.find(class_='article__body')
            if content_div:
                paragraphs = [p.get_text().strip() for p in content_div.find_all(['p', 'h2']) if p.get_text().strip()]
                text_parts.extend(paragraphs)

        if text_parts:
            full_text = "\n\n".join(text_parts)
            return full_text, True
        else:
            return None, True

    except Exception as e:
        print(f"   ❌ Erreur fetch: {e}")
        return None, True

def check_connection(session):
    print("[*] Vérification de la connexion...")
    try:
        test_url = "https://www.lalsace.fr/"
        response = session.get(test_url, timeout=15)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        is_connected = False
        if soup.find(class_='connect-link') or soup.find(class_='user-name') or "Se déconnecter" in response.text:
            is_connected = True
            
        if is_connected:
            print("   ✅ Connecté avec succès !")
            return True
        else:
            print("   ❌ Non connecté (cookie peut-être invalide)")
            return False
    except Exception as e:
        print(f"   ❌ Erreur lors de la vérification: {e}")
        return False

def main():

    print("[*] Démarrage du scraping L'Alsace (Septembre 2025)...")

    

    session = requests.Session()

    session.headers.update(headers)

    for key, value in cookies.items():

        session.cookies.set(key, value, domain=".lalsace.fr")



    is_connected = check_connection(session)

    if not is_connected:

        confirm = input("[?] Continuer quand même (mode limité à 20 articles) ? (y/n) : ")

        if confirm.lower() != 'y':

            return



    conn = get_db_connection()

    cur = conn.cursor()



    limit_sql = "" if is_connected else "LIMIT 20"



    # On cible Septembre 2025 sans contenu

    cur.execute(f"""

        SELECT id, title, link, source 

        FROM \"Article\" 

        WHERE source ILIKE '%Alsace%' 

          AND content IS NULL

          AND link NOT ILIKE '%mag.mulhouse-alsace.fr%'

          AND \"publishedAt\" >= '2025-09-01'

          AND \"publishedAt\" < '2025-10-01'

        ORDER BY \"publishedAt\" DESC

        {limit_sql}

    """)


    articles = cur.fetchall()
    
    if not articles:
        print("Aucun article à traiter.")
        return

    print(f"[*] Traitement de {len(articles)} articles...")

    stats = {
        "total": len(articles),
        "success": 0,
        "short": 0,
        "fetch_fail": 0,
        "db_error": 0,
        "session_lost": False
    }
    
    threshold = 1 if is_connected else 150
    
    for i, (art_id, title, link, source) in enumerate(articles, 1):
        content, session_active = fetch_article_content(session, link)
        
        if not session_active:
            print(f"\n[!] ARRÊT CRITIQUE : La session a été perdue à l'article {i}. Relancez avec un nouveau cookie.")
            stats["session_lost"] = True
            break

        if content:
            length = len(content)
            if length >= threshold:
                try:
                    cur.execute('UPDATE "Article" SET content = %s WHERE id = %s', (content, art_id))
                    conn.commit()
                    print(f"[{i}/{stats['total']}] ✅ {length} chars | {link}")
                    stats["success"] += 1
                except Exception as e:
                    print(f"[{i}/{stats['total']}] ❌ Erreur BDD: {e} | {link}")
                    stats["db_error"] += 1
                    conn.rollback()
            else:
                print(f"[{i}/{stats['total']}] ⚠️ Taille < {threshold} ({length} chars) | {link}")
                stats["short"] += 1
        else:
            print(f"[{i}/{stats['total']}] ❌ Erreur Fetch | {link}")
            stats["fetch_fail"] += 1

    cur.close()
    conn.close()
    
    print("\n" + "="*40)
    print("        COMPTE RENDU DU SCRAPING")
    print("="*40)
    print(f"Articles trouvés au départ : {stats['total']}")
    print(f"Articles mis à jour (✅)   : {stats['success']}")
    print(f"Contenus trop courts (⚠️)  : {stats['short']}")
    print(f"Échecs de chargement (❌) : {stats['fetch_fail']}")
    print(f"Erreurs de base de données : {stats['db_error']}")
    if stats["session_lost"]:
        print(f"Statut final               : 🛑 ARRÊT PRÉCOCE (Session perdue)")
    else:
        print(f"Statut final               : ✨ TERMINÉ")
    print("="*40)

if __name__ == "__main__":
    main()