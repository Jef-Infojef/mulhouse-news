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
    print("=== TEST SCRAPER GITHUB AVEC SECRETS V3 ===")
    db_url, cookies_raw = load_config()
    if not db_url or not cookies_raw: 
        print("❌ Secrets manquants.")
        return

    cookies_dict = {}
    # Nettoyage des guillemets
    clean = cookies_raw.strip().replace('"', '').replace("'", "")
    
    # Parsing manuel robuste
    # On sépare par ';' puis on split seulement sur le PREMIER '=' trouvé pour chaque partie
    parts = [p.strip() for p in clean.split(';') if p.strip()]
    for p in parts:
        if '=' in p:
            name, value = p.split('=', 1)
            name = name.strip()
            value = value.strip()
            
            # Correction des noms de cookies mal formés (ex: ".XCONNECT_SESSION : 2")
            if ':' in name: name = name.split(':')[-1].strip()
            
            # Si le nom est juste "2", c'est la valeur de .XCONNECT_SESSION qui a été mal collée
            if name == "2":
                cookies_dict[".XCONNECT_SESSION"] = f"2={value}"
            else:
                cookies_dict[name] = value

    # Si .XCONNECT_SESSION n'est pas nommé explicitement mais qu'on a une valeur longue
    if ".XCONNECT_SESSION" not in cookies_dict:
        for k, v in list(cookies_dict.items()):
            if v.startswith('2=') and len(v) > 100:
                cookies_dict[".XCONNECT_SESSION"] = cookies_dict.pop(k)
                break

    print(f"[*] Cookies préparés ({len(cookies_dict)}) : {', '.join(cookies_dict.keys())}")
    
    # Debug sécurisé de la longueur du cookie de session
    if ".XCONNECT_SESSION" in cookies_dict:
        sess_len = len(cookies_dict[".XCONNECT_SESSION"])
        print(f"[*] Longueur de la session : {sess_len} caractères")
        if sess_len < 400:
            print("⚠️ ATTENTION : Le cookie de session semble trop court (valeur tronquée ?)")

    test_link = "https://www.lalsace.fr/insolite/2026/01/25/course-d-orientation-quand-l-histoire-industrielle-se-decouvre-un-plan-et-une-boussole-a-la-main"
    content = fetch_content(test_link, cookies_dict)
    
    if content:
        print(f"✅ RÉSULTAT : {len(content)} caractères.")
        if len(content) > 3000:
            print("🚀 SUCCÈS TOTAL AVEC LES SECRETS GITHUB !")
    else:
        print("❌ ÉCHEC : Aucun contenu.")

if __name__ == "__main__":
    main()
