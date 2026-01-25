import os
import psycopg2
from bs4 import BeautifulSoup
import json
import re
from curl_cffi import requests

def load_config():
    db_url = os.environ.get("DATABASE_URL")
    cookies_raw = os.environ.get("ALSACE_COOKIES")
    return db_url, cookies_raw

def fetch_content(url, cookies_dict):
    print(f"[*] Fetching with curl_cffi: {url}")
    try:
        resp = requests.get(
            url, 
            cookies=cookies_dict,
            impersonate="chrome110",
            timeout=30
        )
        
        page_text = resp.text
        # Détection de connexion
        is_connected = any(x in page_text for x in ["Se déconnecter", "Mon compte", "Mon profil", "suscriber"])
        print(f"[*] État session sur GitHub : {'✅ CONNECTÉ' if is_connected else '❌ NON CONNECTÉ'}")
        
        if not is_connected:
            print("[!] Marqueurs non trouvés. Vérifiez si vous voyez 'Se connecter' dans le texte suivant :")
            print(page_text[:500].replace('\n', ' '))

        soup = BeautifulSoup(page_text, 'html.parser')
        text_parts = []
        chapo = soup.find(class_='chapo') or soup.find(class_='article__chapo')
        if chapo: text_parts.append(chapo.get_text().strip())
        
        content_blocks = soup.find_all('div', class_='textComponent')
        for block in content_blocks:
            txt = block.get_text("\n", strip=True)
            if len(txt) > 10: text_parts.append(txt)
            
        return "\n\n".join(text_parts)
    except Exception as e:
        print(f"❌ Erreur fetch : {e}")
        return None

def main():
    print("=== TEST SCRAPER GITHUB AVEC SECRETS V4 ===")
    db_url, cookies_raw = load_config()
    if not db_url or not cookies_raw: 
        print("❌ Secrets manquants.")
        return

    # NETTOYAGE SPÉCIFIQUE POUR LE FORMAT : .XCONNECT_SESSION : "2=..."
    clean = cookies_raw.strip()
    print(f"[*] Raw secret reçu (longueur: {len(clean)})")

    # 1. On enlève les guillemets au début et à la fin s'ils existent
    clean = re.sub(r'^["\']|["\']$', '', clean)
    
    # 2. Si le format est ".XCONNECT_SESSION : "2=...", on extrait la partie après les deux-points
    if ':' in clean:
        parts = clean.split(':', 1)
        # On ne garde que la partie valeur et on enlève les guillemets intérieurs si présents
        clean = parts[1].strip().replace('"', '').replace("'", "")
    
    # 3. Si le format était juste ".XCONNECT_SESSION = 2=...", on gère aussi
    elif clean.startswith('.XCONNECT_SESSION='):
        clean = clean.replace('.XCONNECT_SESSION=', '', 1).strip().replace('"', '').replace("'", "")

    cookies_dict = {
        ".XCONNECT_SESSION": clean,
        ".XCONNECTKeepAlive": "2=1",
        ".XCONNECT": "2=1"
    }

    print(f"[*] Session extraite (début) : {cookies_dict['.XCONNECT_SESSION'][:50]}...")
    print(f"[*] Longueur finale de la session : {len(cookies_dict['.XCONNECT_SESSION'])} caractères")

    test_link = "https://www.lalsace.fr/insolite/2026/01/25/course-d-orientation-quand-l-histoire-industrielle-se-decouvre-un-plan-et-une-boussole-a-la-main"
    content = fetch_content(test_link, cookies_dict)
    
    if content:
        print(f"✅ RÉSULTAT : {len(content)} caractères.")
        if len(content) > 3000:
            print("🚀 SUCCÈS : Le nettoyage du secret a fonctionné !")
    else:
        print("❌ ÉCHEC : Aucun contenu.")

if __name__ == "__main__":
    main()