import os
import psycopg2
from bs4 import BeautifulSoup
import json
import re
from curl_cffi import requests

def load_config():
    db_url = os.environ.get("DATABASE_URL")
    # On récupère le secret configuré sur GitHub
    cookies_raw = os.environ.get("ALSACE_COOKIES")
    
    if not cookies_raw:
        print("❌ ERREUR : Secret ALSACE_COOKIES non trouvé dans l'environnement.")
    else:
        print(f"[*] Secret ALSACE_COOKIES détecté (longueur: {len(cookies_raw)})")
        
    return db_url, cookies_raw

def fetch_content(url, cookies_dict):
    print(f"[*] Fetching with curl_cffi (chrome110): {url}")
    try:
        resp = requests.get(
            url, 
            cookies=cookies_dict,
            impersonate="chrome110",
            timeout=30
        )
        
        page_text = resp.text
        is_connected = any(x in page_text for x in ["Se déconnecter", "Mon compte", "Mon profil", "suscriber"])
        print(f"[*] État session sur GitHub : {'✅ CONNECTÉ' if is_connected else '❌ NON CONNECTÉ'}")
        
        soup = BeautifulSoup(page_text, 'html.parser')
        text_parts = []
        
        # Chapô
        chapo = soup.find(class_='chapo') or soup.find(class_='article__chapo')
        if chapo: text_parts.append(chapo.get_text().strip())
        
        # Corps (textComponent)
        content_blocks = soup.find_all('div', class_='textComponent')
        for block in content_blocks:
            txt = block.get_text("\n", strip=True)
            if len(txt) > 10: text_parts.append(txt)
            
        return "\n\n".join(text_parts)
    except Exception as e:
        print(f"❌ Erreur fetch : {e}")
        return None

def main():
    print("=== TEST SCRAPER GITHUB AVEC SECRETS ===")
    db_url, cookies_raw = load_config()
    if not db_url or not cookies_raw: return

    # Nettoyage et préparation des cookies (logique V10)
    cookies_dict = {}
    clean = cookies_raw.replace('"', '').replace("'", '').strip()
    
    # Si l'utilisateur a mis le préfixe par erreur, on l'enlève
    if 'XCONNECT_SESSION' in clean[:30] and ':' in clean:
        clean = clean.split(':', 1)[1].strip()
    elif 'XCONNECT_SESSION' in clean[:30] and '=' in clean:
        # Cas ".XCONNECT_SESSION=2=..." -> on veut juste "2=..."
        if clean.count('=') >= 2:
            clean = clean.split('=', 1)[1].strip()

    parts = [p.strip() for p in clean.split(';') if '=' in p]
    for p in parts:
        k, v = p.split('=', 1)
        cookies_dict[k.strip()] = v.strip()
    
    # Si on n'a qu'une valeur commençant par 2=, on lui donne le bon nom
    if not cookies_dict and clean.startswith('2='):
        cookies_dict[".XCONNECT_SESSION"] = clean
    elif ".XCONNECT_SESSION" not in cookies_dict:
        # On force le nom pour le premier élément si c'est la session
        first_val = list(cookies_dict.values())[0] if cookies_dict else ""
        if first_val.startswith('2='):
            # On réassigne correctement
            first_key = list(cookies_dict.keys())[0]
            cookies_dict[".XCONNECT_SESSION"] = cookies_dict.pop(first_key)

    print(f"[*] Cookies préparés : {', '.join(cookies_dict.keys())}")

    # Test sur le même article de 4ko
    test_link = "https://www.lalsace.fr/insolite/2026/01/25/course-d-orientation-quand-l-histoire-industrielle-se-decouvre-un-plan-et-une-boussole-a-la-main"
    content = fetch_content(test_link, cookies_dict)
    
    if content:
        print(f"✅ RÉSULTAT : {len(content)} caractères.")
        if len(content) > 3000:
            print("🚀 SUCCÈS : Les Secrets GitHub fonctionnent !")
        else:
            print(f"⚠️ TRONQUÉ : {len(content)}/3927 chars. Vérifiez le format du Secret.")
    else:
        print("❌ ÉCHEC : Aucun contenu.")

if __name__ == "__main__":
    main()
