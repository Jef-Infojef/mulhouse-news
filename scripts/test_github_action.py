import os
import psycopg2
from bs4 import BeautifulSoup
import json
import re
from curl_cffi import requests

# COOKIE EN DUR POUR LES TESTS GITHUB
COOKIES_HARDCODED = ".XCONNECT_SESSION=2=42F647DB9B788CF4E0AFFF1DD52DE98DAC09560B7B8173B6AE707DE13249B5D3D98E26C37209690D989A05961C1E93CBDDF2909ED6FF95194BEA6AE2C1E5A62F519DB83384CA795ACE1E2824AA4C1D00C904F51699D03E6489E9A4B4C8211E0D25B9B66E68555AA3B098E18D1CFB0D8E55CD162A101CF8E23306F0A225ABBE4E6AA1480CEA97DAEF016F99185FECA69B74DCE53DE2A59FB8889A43374A7891008D274391E153481FAF94E8CF51E25A9872DE0D0AA146142A059E319D5BEC9708926A8C25B1A97FBA849A2B64CC973B6CE3700E3E16AB420B9135DE775FE8D9E4AF4D143969441F03400814963FB3C265; .XCONNECTKeepAlive=2=1; .XCONNECT=2=1; _poool=9aab6ee3-fda6-43fc-a90e-29de3c73d8f7"

def load_config():
    db_url = os.environ.get("DATABASE_URL")
    # On utilise le cookie en dur en priorité pour le test
    cookies_raw = COOKIES_HARDCODED
    return db_url, cookies_raw

def fetch_content(url, cookies_dict):
    print(f"[*] Fetching with curl_cffi (impersonate='chrome110'): {url}")
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
        
        if not is_connected:
            print("[!] Marqueurs non trouvés. Extrait du texte de la page :")
            soup_debug = BeautifulSoup(page_text, 'html.parser')
            print(soup_debug.get_text(" ", strip=True)[:500] + "...")

        soup = BeautifulSoup(page_text, 'html.parser')
        text_parts = []
        
        # 1. Chapô
        chapo = soup.find(class_='chapo') or soup.find(class_='article__chapo')
        if chapo: text_parts.append(chapo.get_text().strip())
        
        # 2. Corps
        content_blocks = soup.find_all('div', class_='textComponent')
        for block in content_blocks:
            txt = block.get_text("\n", strip=True)
            if len(txt) > 10: text_parts.append(txt)
            
        # 3. Fallback LD+JSON
        if not text_parts or len("\n".join(text_parts)) < 300:
            for script in soup.find_all('script', type='application/ld+json'):
                try:
                    data = json.loads(script.string)
                    items = data if isinstance(data, list) else [data]
                    for item in items:
                        if item.get('@type') in ['VideoObject', 'NewsArticle'] and item.get('description'):
                            text_parts.append(item['description'].strip())
                except: pass

        return "\n\n".join(text_parts)
    except Exception as e:
        print(f"❌ Erreur fetch : {e}")
        return None

def main():
    print("=== TEST SCRAPER GITHUB ACTIONS V10 (HARDCODED COOKIES) ===")
    db_url, cookies_raw = load_config()
    if not db_url: return

    # Préparation des cookies
    cookies_dict = {}
    parts = [p.strip() for p in cookies_raw.split(';') if '=' in p]
    for p in parts:
        k, v = p.split('=', 1)
        cookies_dict[k.strip()] = v.strip()
    
    print(f"[*] Cookies injectés : {', '.join(cookies_dict.keys())}")

    # Test sur l'article de 4ko
    test_link = "https://www.lalsace.fr/insolite/2026/01/25/course-d-orientation-quand-l-histoire-industrielle-se-decouvre-un-plan-et-une-boussole-a-la-main"
    content = fetch_content(test_link, cookies_dict)
    
    if content:
        print(f"✅ RÉSULTAT : {len(content)} caractères.")
        if len(content) > 3000:
            print("🚀 SUCCÈS TOTAL SUR GITHUB !")
        else:
            print(f"⚠️ TRONQUÉ : {len(content)}/3927 chars.")
    else:
        print("❌ ÉCHEC : Aucun contenu.")

if __name__ == "__main__":
    main()