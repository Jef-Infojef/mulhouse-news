import os
import requests
import psycopg2
from bs4 import BeautifulSoup
from dotenv import load_dotenv
import time
import random

# Configuration
def load_env():
    root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    env_files = [".envenv", ".env.local", ".env"]
    found = False
    for f in env_files:
        path = os.path.join(root_dir, f)
        if os.path.exists(path):
            load_dotenv(path)
            if os.environ.get("DATABASE_URL"):
                print(f"[*] Configuration chargée depuis {f}")
                found = True
                break
    if not found:
        load_dotenv()

load_env()
DATABASE_URL = os.environ.get("DATABASE_URL")

# Nouveau cookie fourni le 25/01/2026
COOKIES_RAW = ".XCONNECT_SESSION=2=42F647DB9B788CF4E0AFFF1DD52DE98D61E04266014358F8D5CEEC0A98C9154AC0E9FE63D6A073F43F29D117C58F183AC9C16474B604D38ACE590BCACBED29E2416ACDD4239CBE58CAD4AC3000535BD0DBA83729F0A40EC368C47A39B10282E7BCD193A47FDB854878F60911EC373FD6F65D9C15543158561DD3425A7B5CAB0DC5E4F3A707826178AD6E4B729A897548ECF22EF0B0B57D5E80E44F3761444728EDA573B65D138677117A07756EB9D2F01F350B268F6E29526412BD9826E655EBCD17E77FDA5BA787EADB87619D27896DA6A4F144081B021C19646B0C7270185353B2BE94480F1AE522D87E032200D15E; .XCONNECTKeepAlive=2=1; .XCONNECT=2=1; _poool=9aab6ee3-fda6-43fc-a90e-29de3c73d8f7; domain=lalsace.fr; path=/; secure; HttpOnly; SameSite=Lax"

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
    url = DATABASE_URL
    if url and "DATABASE_URL=\"" in url:
        url = url.replace("DATABASE_URL=\"", "").replace("\"", "")
    if url and "?pgbouncer=true" in url:
        url = url.replace("?pgbouncer=true", "")
    return psycopg2.connect(url)

def fetch_article_content(session, url):
    try:
        time.sleep(random.uniform(0.7, 1.5))
        response = session.get(url, timeout=15)
        if response.status_code != 200:
            return None, True
        
        is_still_connected = "Se déconnecter" in response.text or "mon compte" in response.text.lower()
        if not is_still_connected:
            return None, False

        soup = BeautifulSoup(response.text, 'html.parser')
        text_parts = []
        
        chapo = soup.find(class_='chapo') or soup.find(class_='article__chapo')
        if chapo: text_parts.append(chapo.get_text().strip())

        for modal in soup.find_all(class_='GXCO_content'): modal.decompose()
            
        content_blocks = soup.find_all('div', class_='textComponent')
        if content_blocks:
            for block in content_blocks:
                block_text = block.get_text("\n", strip=True)
                if block_text and len(block_text) > 10:
                    text_parts.append(block_text)
        
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
        return None, True
    except Exception as e:
        print(f"   ❌ Erreur fetch: {e}")
        return None, True

def check_connection(session):
    print("[*] Vérification de la connexion...")
    try:
        response = session.get("https://www.lalsace.fr/", timeout=15)
        if "Se déconnecter" in response.text or "Mon compte" in response.text:
            print("   ✅ Connecté avec succès !")
            return True
        print("   ❌ Non connecté (cookie invalide)")
        return False
    except Exception as e:
        print(f"   ❌ Erreur vérification: {e}")
        return False

def main():
    print("[*] Démarrage du scraping L'Alsace (Année 2021)...")
    session = requests.Session()
    session.headers.update(headers)
    for key, value in cookies.items():
        session.cookies.set(key, value, domain=".lalsace.fr")

    is_connected = check_connection(session)
    if not is_connected:
        print("   ⚠️ Mode sans connexion (limité aux articles gratuits)")
        confirm = input("[?] Continuer quand même ? (y/n) : ")
        if confirm.lower() != 'y': return

    conn = get_db_connection()
    cur = conn.cursor()

    # Ciblage spécifique de 2021
    cur.execute("""
        SELECT id, title, link, \"publishedAt\" 
        FROM \"Article\" 
        WHERE (source ILIKE '%Alsace%' OR link LIKE '%lalsace.fr%')
          AND content IS NULL
          AND \"publishedAt\" >= '2021-01-01'
          AND \"publishedAt\" <= '2021-12-31'
        ORDER BY \"publishedAt\" DESC
    """)
    articles = cur.fetchall()
    
    if not articles:
        print("Aucun article de 2021 sans contenu trouvé.")
        return

    print(f"[*] Traitement de {len(articles)} articles pour 2021...")
    stats = {"success": 0, "fail": 0, "session_lost": False}
    threshold = 150
    
    for i, (art_id, title, link, pub_date) in enumerate(articles, 1):
        content, session_active = fetch_article_content(session, link)
        if not session_active:
            print(f"\n[!] ARRÊT CRITIQUE : Session perdue à l'article {i}.")
            stats["session_lost"] = True
            break
        
        if content and len(content) >= threshold:
            try:
                cur.execute('UPDATE "Article" SET content = %s WHERE id = %s', (content, art_id))
                conn.commit()
                print(f"[{i}/{len(articles)}] ✅ {pub_date.strftime('%d/%m/%Y')} | {len(content)} chars | {link}")
                stats["success"] += 1
            except Exception as e:
                conn.rollback()
                print(f"[{i}/{len(articles)}] ❌ Erreur BDD: {e}")
                stats["fail"] += 1
        else:
            print(f"[{i}/{len(articles)}] ⚠️ {pub_date.strftime('%d/%m/%Y')} | Erreur/Court | {link}")
            stats["fail"] += 1

    cur.close()
    conn.close()
    print("\n" + "="*40)
    print(f"COMPTE RENDU 2021")
    print(f"Succès : {stats['success']}/{len(articles)}")
    print("="*40)

if __name__ == "__main__":
    main()