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
                print(f"[*] Loaded configuration from {f}")
                found = True
                break
    if not found:
        load_dotenv(".env.local")
        load_dotenv(".env")

load_env()
DATABASE_URL = os.environ.get("DATABASE_URL")

# Le cookie fourni par l'utilisateur (à mettre à jour si nécessaire)
COOKIES_RAW = ".XCONNECT_SESSION=2=42F647DB9B788CF4E0AFFF1DD52DE98D1A223A8CACD85179B5AFEDE4613F2FB300A50199684A672D5FC763A5324F4F7D1DCB064D436B1D4E1994D8D8E43BB26ADC291BA3194FE3356DA9675EC063E526F8A085110CCCD7901D40164049242A13759468C20B3DAC6ACAC68BB6FD4C3FCD2FDC22B576882FF782E041836FB7C9AB5991C03E732FC1C1D92C167AA3C894D41050231E36B1B5B1E43A2F50709B75CA072120C89B756886539D39D0118E6FD8C34F5A835A16B4DBB9CB9878831C98506C1B5152A275A495284C67F08F0AF2222DBD86DDFB5FF405F846D832756184AFAB59A0159E82813222CE66978CF0A0D2; .XCONNECTKeepAlive=2=1; .XCONNECT=2=1; _poool=9aab6ee3-fda6-43fc-a90e-29de3c73d8f7; domain=lalsace.fr; path=/; secure; HttpOnly; SameSite=Lax"

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
    if url and "?pgbouncer=true" in url:
        url = url.replace("?pgbouncer=true", "")
    return psycopg2.connect(url)

def fetch_article_content(session, url):
    try:
        time.sleep(random.uniform(0.5, 1.5))
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
                except:
                    pass

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
        soup = BeautifulSoup(response.text, 'html.parser')
        if soup.find(class_='connect-link') or soup.find(class_='user-name') or "Se déconnecter" in response.text:
            print("   ✅ Connecté avec succès !")
            return True
        print("   ❌ Non connecté (cookie invalide)")
        return False
    except Exception as e:
        print(f"   ❌ Erreur vérification: {e}")
        return False

def main():
    print("[*] Démarrage du scraping L'Alsace (Année 2022)...")
    session = requests.Session()
    session.headers.update(headers)
    for key, value in cookies.items():
        session.cookies.set(key, value, domain=".lalsace.fr")

    is_connected = check_connection(session)
    if not is_connected:
        print("   ⚠️ Mode sans connexion (limité aux articles gratuits)")
        confirm = input("[?] Continuer quand même (limite 20) ? (y/n) : ")
        if confirm.lower() != 'y': return

    conn = get_db_connection()
    cur = conn.cursor()
    limit_sql = "" if is_connected else "LIMIT 20"

    # Ciblage de l'année 2022
    cur.execute(f"""
        SELECT id, title, link, source 
        FROM \"Article\" 
        WHERE source ILIKE '%Alsace%' 
          AND content IS NULL
          AND link LIKE '%www.lalsace.fr%'
          AND \"publishedAt\" >= '2022-01-01'
          AND \"publishedAt\" < '2023-01-01'
        ORDER BY \"publishedAt\" DESC
        {limit_sql}
    """)
    articles = cur.fetchall()
    
    if not articles:
        print("Aucun article de 2022 sans contenu trouvé.")
        return

    print(f"[*] Traitement de {len(articles)} articles...")
    stats = {"total": len(articles), "success": 0, "short": 0, "fail": 0, "session_lost": False}
    threshold = 1 if is_connected else 150
    
    for i, (art_id, title, link, source) in enumerate(articles, 1):
        content, session_active = fetch_article_content(session, link)
        if not session_active:
            print(f"\n[!] ARRÊT CRITIQUE : Session perdue à l'article {i}.")
            stats["session_lost"] = True
            break
        if content and len(content) >= threshold:
            try:
                cur.execute('UPDATE "Article" SET content = %s WHERE id = %s', (content, art_id))
                conn.commit()
                print(f"[{i}/{stats['total']}] ✅ {len(content)} chars | {link}")
                stats["success"] += 1
            except Exception as e:
                conn.rollback()
                print(f"[{i}/{stats['total']}] ❌ Erreur BDD: {e}")
                stats["fail"] += 1
        else:
            print(f"[{i}/{stats['total']}] ⚠️ Erreur/Vide/Court | {link}")
            stats["fail"] += 1

    cur.close()
    conn.close()
    print("\n" + "="*40 + "\n        COMPTE RENDU 2022\n" + "="*40)
    print(f"Articles traités : {stats['success']}/{stats['total']}")
    if stats["session_lost"]:
        print("Statut : 🛑 ARRÊT (Session perdue)")
    else:
        print("Statut : ✨ TERMINÉ")
    print("="*40)

if __name__ == "__main__":
    main()
