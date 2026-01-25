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
    print("=== TEST SCRAPER GITHUB AVEC SECRETS V2 ===")
    db_url, cookies_raw = load_config()
    if not db_url or not cookies_raw: return

    cookies_dict = {}
    # Nettoyage des caractères invisibles et guillemets
    clean = cookies_raw.strip().replace('"', '').replace("'", "")
    
    # Extraction de TOUTES les paires Nom=Valeur
    # Si le secret est ".XCONNECT_SESSION : 2=ABC; .X...", on cherche ce qui ressemble à des cookies
    found_pairs = re.findall(r'([^;=\s]+)\s*=\s*([^;]+)', clean)
    
    for name, value in found_pairs:
        name = name.strip()
        value = value.strip()
        
        # Correction automatique si le nom est "2" ou commence par un point bizarre
        if name == "2" or len(value) > 400:
            # Si la valeur est très longue ou que le nom est "2", c'est la session
            if name == "2":
                cookies_dict[".XCONNECT_SESSION"] = f"2={value}"
            else:
                cookies_dict[".XCONNECT_SESSION"] = value
        else:
            cookies_dict[name] = value

    # Si après ça on n'a toujours pas .XCONNECT_SESSION mais qu'on a un truc qui ressemble
    if ".XCONNECT_SESSION" not in cookies_dict:
        # On cherche la valeur la plus longue
        longest_key = max(cookies_dict.keys(), key=lambda k: len(cookies_dict[k]), default=None)
        if longest_key and len(cookies_dict[longest_key]) > 100:
            cookies_dict[".XCONNECT_SESSION"] = cookies_dict.pop(longest_key)

    print(f"[*] Cookies préparés : {', '.join(cookies_dict.keys())}")

    test_link = "https://www.lalsace.fr/insolite/2026/01/25/course-d-orientation-quand-l-histoire-industrielle-se-decouvre-un-plan-et-une-boussole-a-la-main"
    content = fetch_content(test_link, cookies_dict)
    
    if content:
        print(f"✅ RÉSULTAT : {len(content)} caractères.")
        if len(content) > 3000:
            print("🚀 SUCCÈS : Les Secrets GitHub fonctionnent enfin !")
        else:
            print(f"⚠️ TRONQUÉ : {len(content)}/3927 chars.")
    else:
        print("❌ ÉCHEC : Aucun contenu.")

if __name__ == "__main__":
    main()