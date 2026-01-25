import os
import requests
import psycopg2
from bs4 import BeautifulSoup
import json

def load_config():
    db_url = os.environ.get("DATABASE_URL")
    cookies_raw = os.environ.get("ALSACE_COOKIES")
    if cookies_raw:
        print(f"[*] Secret ALSACE_COOKIES détecté (longueur: {len(cookies_raw)})")
    return db_url, cookies_raw

def fetch_content(session, url):
    print(f"[*] Fetching: {url}")
    try:
        resp = session.get(url, timeout=20)
        page_text = resp.text
        
        # Analyse fine des marqueurs
        has_logout = "Se déconnecter" in page_text
        has_account = "Mon compte" in page_text or "Mon profil" in page_text.lower()
        has_premium = "premium" in page_text.lower() or "suscriber" in page_text.lower()
        has_login_btn = "Se connecter" in page_text
        has_subscribe_btn = "S'abonner" in page_text
        
        print(f"[*] Analyse des marqueurs :")
        print(f"    - 'Se déconnecter' : {has_logout}")
        print(f"    - 'Mon compte/profil' : {has_account}")
        print(f"    - 'Premium/Subscriber' : {has_premium}")
        print(f"    - 'Se connecter' (bouton) : {has_login_btn}")
        print(f"    - 'S'abonner' (bouton) : {has_subscribe_btn}")

        is_connected = has_logout or has_account
        print(f"[*] État session final : {'✅ CONNECTÉ' if is_connected else '❌ NON CONNECTÉ'}")
        
        soup = BeautifulSoup(page_text, 'html.parser')
        text_parts = []
        
        # Chapô
        chapo = soup.find(class_='chapo') or soup.find(class_='article__chapo')
        if chapo: text_parts.append(chapo.get_text().strip())
        
        # Corps
        content_blocks = soup.find_all('div', class_='textComponent')
        for block in content_blocks:
            txt = block.get_text("\n", strip=True)
            if len(txt) > 10: text_parts.append(txt)
            
        # LD+JSON
        if not text_parts or len("\n".join(text_parts)) < 300:
            for script in soup.find_all('script', type='application/ld+json'):
                try:
                    data = json.loads(script.string)
                    items = data if isinstance(data, list) else [data]
                    for item in items:
                        if item.get('@type') in ['VideoObject', 'NewsArticle'] and item.get('description'):
                            desc = item['description'].strip()
                            if len(desc) > 100: text_parts.append(desc)
                except: pass

        return "\n\n".join(text_parts)
    except Exception as e:
        print(f"❌ Erreur fetch : {e}")
        return None

def main():
    print("=== TEST SCRAPER GITHUB ACTIONS V7 ===")
    db_url, cookies_raw = load_config()
    if not db_url: return

    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
    })
    
    if cookies_raw:
        raw = cookies_raw.strip().replace('"', '').replace("'", "")
        # Si le secret ne commence pas par .XCONNECT_SESSION, on l'ajoute pour aider le header
        if not raw.startswith('.') and 'XCONNECT' not in raw[:20]:
            raw = f".XCONNECT_SESSION={raw}"
            print("[*] Préfixe .XCONNECT_SESSION ajouté automatiquement.")
        
        session.headers['Cookie'] = raw
        print("[*] Cookies injectés.")

    try:
        # Test sur l'article spécifique de 4ko
        test_link = "https://www.lalsace.fr/insolite/2026/01/25/course-d-orientation-quand-l-histoire-industrielle-se-decouvre-un-plan-et-une-boussole-a-la-main"
        print(f"[*] Article de test (4ko) : {test_link}")
        content = fetch_content(session, test_link)
        if content:
            print(f"✅ RÉSULTAT : {len(content)} caractères.")
            if len(content) > 3000:
                print("🚀 LA SESSION FONCTIONNE PARFAITEMENT SUR GITHUB !")
            else:
                print(f"⚠️ ATTENTION : Seulement {len(content)}/3927 caractères récupérés. Session probablement inactive.")
        else:
            print("❌ RÉSULTAT : Vide.")
    except Exception as e:
        print(f"❌ Erreur BDD : {e}")

if __name__ == "__main__":
    main()
