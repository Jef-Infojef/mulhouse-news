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
COOKIES_RAW = ".XCONNECT_SESSION=2=42F647DB9B788CF4E0AFFF1DD52DE98D60E52BEF914E063E3FBB44C25D1ADCDFB4D07942CC23023863D1DBFC740DCF017BBA2DD0F2BFBAD53F5C3DC290C950D00AE011EDE7728D9CEA964DD8C494369F5E26FC2CD2E260234D9D0E7079A664601366BBF4B6F192F7F8A13999E9EF2F5710E0DF757B16345EFD9208C1B0029DF50E8BA2F6A95697517DDBFB9FE59EF63ACA0D15CAEC22E9F5C580B1723FC163322F2B97198DFD9663CD737367226C1D511A361B8B32B7BE9A2234ABEA8EA305F3423040EA885D09E00F437E9489541837870382316CB23CFFDF0C3F107BE334EF0CCB65D0A34772C3511997454BAF9CF5; .XCONNECTKeepAlive=2=1; .XCONNECT=2=1; _poool=9aab6ee3-fda6-43fc-a90e-29de3c73d8f7; domain=lalsace.fr; path=/; secure; HttpOnly; SameSite=Lax"

# Parsing du cookie brut pour requests
cookies = {}
for part in COOKIES_RAW.split(';'):
    if '=' in part:
        key, value = part.strip().split('=', 1)
        cookies[key] = value

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
    'Accept-Language': 'fr-FR,fr;q=0.9,en-US;q=0.8,en;q=0.7',
    'Accept-Encoding': 'gzip, deflate, br',
    'Connection': 'keep-alive',
    'Upgrade-Insecure-Requests': '1',
    'Sec-Fetch-Dest': 'document',
    'Sec-Fetch-Mode': 'navigate',
    'Sec-Fetch-Site': 'none',
    'Sec-Fetch-User': '?1',
    'Cache-Control': 'max-age=0',
}

def get_db_connection():
    # Nettoyage de l'URL pour psycopg2 (suppression du paramètre pgbouncer non supporté)
    url = DATABASE_URL
    if url and "?pgbouncer=true" in url:
        url = url.replace("?pgbouncer=true", "")
    return psycopg2.connect(url)

def clean_text(text):
    if not text: return None
    return text.strip()

def fetch_article_content(session, url):
    try:
        time.sleep(random.uniform(0.5, 1.5)) # Pause polie
        response = session.get(url, timeout=15)
        
        if response.status_code != 200:
            print(f"   ⚠️ Status {response.status_code}")
            return None

        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Détection Paywall
        if soup.find(class_='paywall') or soup.find(class_='paywall1') or soup.find(id='paywall'):
            pass # Discret

        # Sélecteurs potentiels pour le contenu principal
        text_parts = []
        
        # 1. Le titre (pour le contexte, optionnel mais utile)
        # title = soup.find('h1')
        # if title: text_parts.append(title.get_text().strip())

        # 2. Le Chapô
        chapo = soup.find(class_='chapo') or soup.find(class_='article__chapo')
        if chapo:
            text_parts.append(chapo.get_text().strip())

        # 3. Le corps de l'article (recherche de tous les blocs textComponent)
        # On ignore la modale de connexion qui polluait le texte
        for modal in soup.find_all(class_='GXCO_content'):
            modal.decompose()
            
        content_blocks = soup.find_all('div', class_='textComponent')
        if content_blocks:
            for block in content_blocks:
                # On récupère le texte du bloc (paragraphes et titres h2)
                block_text = block.get_text("\n", strip=True)
                if block_text and len(block_text) > 10:
                    text_parts.append(block_text)
        else:
            # Fallback si textComponent n'est pas utilisé (ancienne structure EBRA)
            content_div = soup.find('div', class_='c-article-content') or \
                          soup.find('div', itemprop='articleBody') or \
                          soup.find(class_='article__body')
            if content_div:
                paragraphs = [p.get_text().strip() for p in content_div.find_all(['p', 'h2']) if p.get_text().strip()]
                text_parts.extend(paragraphs)

        if text_parts:
            # On retire les doublons potentiels et on nettoie
            full_text = "\n\n".join(text_parts)
            return full_text
        else:
            print("   ⚠️ Aucun contenu trouvé (ni chapô ni corps)")
            return None

    except Exception as e:
        print(f"   ❌ Erreur fetch: {e}")
        return None

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
    print("[*] Démarrage du scraping L'Alsace (Oct-Nov 2025)...")
    
    # Initialisation de la session avec headers et cookies
    session = requests.Session()
    session.headers.update(headers)
    for key, value in cookies.items():
        session.cookies.set(key, value, domain=".lalsace.fr")

    if not check_connection(session):
        confirm = input("[?] Continuer quand même ? (y/n) : ")
        if confirm.lower() != 'y':
            return

    conn = get_db_connection()
    cur = conn.cursor()

    # On cible Octobre et Novembre 2025 sans contenu
    cur.execute("""
        SELECT id, title, link, source 
        FROM \"Article\" 
        WHERE source ILIKE '%Alsace%' 
          AND content IS NULL
          AND \"publishedAt\" >= '2025-10-01'
          AND \"publishedAt\" < '2025-12-01'
        ORDER BY \"publishedAt\" DESC
        LIMIT 200
    """)
    articles = cur.fetchall()
    
    if not articles:
        print("Aucun article à traiter.")
        return

    print(f"[*] Traitement de {len(articles)} articles...")

    success_count = 0
    for i, (art_id, title, link, source) in enumerate(articles, 1):
        content = fetch_article_content(session, link)
        
        if content:
            length = len(content)
            if length >= 1000:
                try:
                    cur.execute('UPDATE "Article" SET content = %s WHERE id = %s', (content, art_id))
                    conn.commit()
                    print(f"[{i}/{len(articles)}] ✅ {length} chars | {link}")
                    success_count += 1
                except Exception as e:
                    print(f"[{i}/{len(articles)}] ❌ Erreur BDD: {e} | {link}")
                    conn.rollback()
            else:
                print(f"[{i}/{len(articles)}] ⚠️ Taille < 1000 ({length} chars) | {link}")
        else:
            print(f"[{i}/{len(articles)}] ❌ Erreur Fetch | {link}")

    cur.close()
    conn.close()
    print(f"\n[*] Terminé. {success_count} articles mis à jour.")

    cur.close()
    conn.close()
    print(f"\n[*] Terminé. {success_count} articles mis à jour.")

if __name__ == "__main__":
    main()
