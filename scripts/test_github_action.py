import os
import requests
import psycopg2
from bs4 import BeautifulSoup
import json
import re

def load_config():
    db_url = os.environ.get("DATABASE_URL")
    cookies_raw = os.environ.get("ALSACE_COOKIES")
    return db_url, cookies_raw

def fetch_content(session, url):
    print(f"[*] Fetching: {url}")
    try:
        resp = session.get(url, timeout=20)
        
        # Debug Cookies réellement envoyés
        sent = session.cookies.get_dict()
        print(f"[*] Cookies en session ({len(sent)}) : {', '.join(sent.keys())}")

        # Détection de connexion plus fiable
        page_text = resp.text
        is_connected = "Se déconnecter" in page_text
        has_login_btn = "Se connecter" in page_text
        
        print(f"[*] Marqueur 'Se déconnecter' présent : {is_connected}")
        print(f"[*] Marqueur 'Se connecter' présent : {has_login_btn}")
        
        if is_connected:
            print("   ✅ Statut : RÉELLEMENT CONNECTÉ")
        else:
            print("   ❌ Statut : NON CONNECTÉ")

        soup = BeautifulSoup(resp.text, 'html.parser')
        text_parts = []
        
        # 1. Chapô
        chapo = soup.find(class_='chapo') or soup.find(class_='article__chapo')
        if chapo: 
            print("   ✅ Chapô extrait")
            text_parts.append(chapo.get_text().strip())
        
        # 2. Corps
        content_blocks = soup.find_all('div', class_='textComponent')
        if content_blocks:
            print(f"   ✅ {len(content_blocks)} blocs texte extraits")
            for block in content_blocks:
                txt = block.get_text("\n", strip=True)
                if len(txt) > 10: text_parts.append(txt)
            
        # 3. LD+JSON (Vidéo)
        scripts = soup.find_all('script', type='application/ld+json')
        for script in scripts:
            try:
                data = json.loads(script.string)
                items = data if isinstance(data, list) else [data]
                for item in items:
                    t = item.get('@type')
                    print(f"   🔍 LD+JSON type trouvé : {t}")
                    if t in ['VideoObject', 'NewsArticle'] and item.get('description'):
                        desc = item['description'].strip()
                        if len(desc) > 100:
                            print(f"   ✅ Description extraite du JSON ({t})")
                            text_parts.append(desc)
            except: pass

        return "\n\n".join(text_parts)
    except Exception as e:
        print(f"❌ Erreur fetch : {e}")
        return None

def main():
    print("=== TEST SCRAPER GITHUB ACTIONS V4 ===")
    db_url, cookies_raw = load_config()
    if not db_url: return

    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
        'Accept-Language': 'fr-FR,fr;q=0.9',
    })
    
    if cookies_raw:
        # Nettoyage agressif des cookies (enlève guillemets, espaces, et préfixe si présent)
        # On cherche des paires clé=valeur
        raw = cookies_raw.replace('"', '').replace("'", "")
        # Si l'utilisateur a collé ".XCONNECT_SESSION : 2=...", on enlève le préfixe
        if ':' in raw and '=' in raw and raw.find(':') < raw.find('='):
            raw = raw.split(':', 1)[1].strip()
            
        print(f"[*] Raw cookies après nettoyage (début) : {raw[:50]}...")
        
        parts = [p.strip() for p in raw.split(';') if '=' in p]
        for p in parts:
            try:
                k, v = p.split('=', 1)
                session.cookies.set(k.strip(), v.strip(), domain=".lalsace.fr")
            except: pass

    try:
        url = db_url.replace("?pgbouncer=true", "")
        conn = psycopg2.connect(url)
        cur = conn.cursor()
        cur.execute("""
            SELECT title, link FROM \"Article\" 
            WHERE source ILIKE '%Alsace%' AND link LIKE '%www.lalsace.fr%' AND content IS NULL 
            ORDER BY \"publishedAt\" DESC LIMIT 1
        """)
        article = cur.fetchone()
        if article:
            print(f"[*] Article : {article[0]}")
            content = fetch_content(session, article[1])
            if content:
                print(f"✅ RÉSULTAT : {len(content)} chars.")
            else:
                print("❌ RÉSULTAT : Vide.")
        cur.close()
        conn.close()
    except Exception as e:
        print(f"❌ Erreur BDD : {e}")

if __name__ == "__main__":
    main()