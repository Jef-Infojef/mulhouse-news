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
        # On limite les redirections pour voir le problème
        resp = requests.get(
            url, 
            cookies=cookies_dict,
            impersonate="chrome110",
            timeout=30,
            allow_redirects=True,
            max_redirects=5
        )
        
        print(f"[*] Final URL after redirects: {resp.url}")
        print(f"[*] Status Code: {resp.status_code}")
        
        page_text = resp.text
        is_connected = any(x in page_text for x in ["Se déconnecter", "Mon compte", "Mon profil", "suscriber"])
        print(f"[*] État session : {'✅ CONNECTÉ' if is_connected else '❌ NON CONNECTÉ'}")
        
        if not is_connected:
            print("[!] Marqueurs non trouvés. Extrait du texte :")
            print(BeautifulSoup(page_text, 'html.parser').get_text(" ")[:500] + "...")

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
    print("=== TEST SCRAPER GITHUB AVEC SECRETS V5 ===")
    db_url, cookies_raw = load_config()
    if not db_url or not cookies_raw: 
        print("❌ Secrets manquants.")
        return

    # NETTOYAGE ROBUSTE
    clean = cookies_raw.strip()
    print(f"[*] Raw secret reçu (longueur: {len(clean)})")

    # Enlever les guillemets et préfixes
    clean = re.sub(r'^["\']|["\']$', '', clean)
    if ':' in clean: clean = clean.split(':', 1)[1].strip()
    clean = clean.replace('"', '').replace("'", "").strip()

    cookies_dict = {
        ".XCONNECT_SESSION": clean,
        ".XCONNECTKeepAlive": "2=1",
        ".XCONNECT": "2=1",
        "_poool": "9aab6ee3-fda6-43fc-a90e-29de3c73d8f7"
    }

    # Debug sécurisé
    val = cookies_dict['.XCONNECT_SESSION']
    print(f"[*] Session extraite (début) : {val[:20]}...{val[-20:]} (Len: {len(val)})")

    test_link = "https://www.lalsace.fr/insolite/2026/01/25/course-d-orientation-quand-l-histoire-industrielle-se-decouvre-un-plan-et-une-boussole-a-la-main"
    content = fetch_content(test_link, cookies_dict)
    
    if content:
        print(f"✅ RÉSULTAT : {len(content)} caractères.")
    else:
        print("❌ ÉCHEC : Aucun contenu.")

if __name__ == "__main__":
    main()
