import os
from curl_cffi import requests
import psycopg2
from bs4 import BeautifulSoup
from dotenv import load_dotenv

# Configuration
load_dotenv(".envenv")
load_dotenv(".env.local")
load_dotenv(".env")

DATABASE_URL = os.environ.get("DATABASE_URL")
ALSACE_COOKIES = os.environ.get("ALSACE_COOKIES")

def get_db_connection():
    url = DATABASE_URL
    if url and "?pgbouncer=true" in url: url = url.replace("?pgbouncer=true", "").replace("&pgbouncer=true", "")
    return psycopg2.connect(url)

def test_one():
    # Cookie dict preparation
    cookies_dict = {}
    if ALSACE_COOKIES:
        clean = ALSACE_COOKIES.strip().replace('"', '').replace("'", "")
        if ':' in clean: clean = clean.split(':', 1)[1].strip()
        cookies_dict = {".XCONNECT_SESSION": clean, ".XCONNECTKeepAlive": "2=1", ".XCONNECT": "2=1", "_poool": "9aab6ee3-fda6-43fc-a90e-29de3c73d8f7"}

    # Target URL (un article payant récent)
    link = "https://www.lalsace.fr/faits-divers-justice/2026/01/27/le-procureur-dresse-le-bilan-de-sa-premiere-annee-a-mulhouse"
    
    print(f"[*] Test sur : {link}")
    
    try:
        response = requests.get(link, cookies=cookies_dict, impersonate="chrome110", timeout=15)
        
        is_connected = any(x in response.text for x in ["Se déconnecter", "Mon compte", "Mon profil", "premium"])
        print(f"Connexion active : {'✅ OUI' if is_connected else '❌ NON'}")

        soup = BeautifulSoup(response.text, 'html.parser')
        text_parts = []
        
        # Chapô
        chapo = soup.find(class_='chapo') or soup.find(class_='article__chapo')
        if chapo: text_parts.append(chapo.get_text().strip())

        # Blocs de texte (textComponent)
        content_blocks = soup.find_all('div', class_='textComponent')
        if content_blocks:
            for block in content_blocks:
                txt = block.get_text("\n", strip=True)
                if txt and len(txt) > 10:
                    text_parts.append(txt)

        full_text = "\n\n".join(text_parts)
        print("\n=== CONTENU RÉCUPÉRÉ ===\n")
        print(full_text[:1000] + ("..." if len(full_text) > 1000 else ""))
        print("\n========================\n")
        print(f"Longueur : {len(full_text)} caractères")

    except Exception as e:
        print(f"Erreur : {e}")

if __name__ == "__main__":
    test_one()
