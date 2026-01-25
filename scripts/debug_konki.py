import os
import requests
from bs4 import BeautifulSoup

COOKIES_RAW = ".XCONNECT_SESSION=2=42F647DB9B788CF4E0AFFF1DD52DE98D60E52BEF914E063E3FBB44C25D1ADCDFB4D07942CC23023863D1DBFC740DCF017BBA2DD0F2BFBAD53F5C3DC290C950D00AE011EDE7728D9CEA964DD8C494369F5E26FC2CD2E260234D9D0E7079A664601366BBF4B6F192F7F8A13999E9EF2F5710E0DF757B16345EFD9208C1B0029DF50E8BA2F6A95697517DDBFB9FE59EF63ACA0D15CAEC22E9F5C580B1723FC163322F2B97198DFD9663CD737367226C1D511A361B8B32B7BE9A2234ABEA8EA305F3423040EA885D09E00F437E9489541837870382316CB23CFFDF0C3F107BE334EF0CCB65D0A34772C3511997454BAF9CF5; .XCONNECTKeepAlive=2=1; .XCONNECT=2=1; _poool=9aab6ee3-fda6-43fc-a90e-29de3c73d8f7"

cookies = {}
for part in COOKIES_RAW.split(';'):
    if '=' in part:
        key, value = part.strip().split('=', 1)
        cookies[key] = value

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
    'Accept-Language': 'fr-FR,fr;q=0.9',
}

def debug_article():
    url = "https://www.lalsace.fr/sport/2026/01/23/yannick-konki-quitte-le-fc-mulhouse-pour-vesoul"
    session = requests.Session()
    session.headers.update(headers)
    for key, value in cookies.items():
        session.cookies.set(key, value, domain=".lalsace.fr")

    try:
        response = session.get(url, timeout=15)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        print(f"[*] Analyse de l\'article : {url}")
        
        # 1. Vérification du Chapô
        chapo = soup.find(class_='chapo') or soup.find(class_='article__chapo')
        if chapo:
            print(f"   ✅ Chapô trouvé ({len(chapo.get_text())} chars)")
        else:
            print("   ❌ Aucun chapô trouvé")

        # 2. Recherche de textComponent
        content_blocks = soup.find_all('div', class_='textComponent')
        print(f"   🔍 Nombre de blocs textComponent : {len(content_blocks)}")
        
        for i, block in enumerate(content_blocks, 1):
            txt = block.get_text(strip=True)
            print(f"      - Bloc {i} : {len(txt)} chars")

        # 3. Sauvegarde du HTML pour inspection
        with open("debug_article_konki.html", "w", encoding="utf-8") as f:
            f.write(response.text)
            
        print("\n[*] HTML sauvegardé dans debug_article_konki.html")

    except Exception as e:
        print(f"❌ Erreur : {e}")

if __name__ == "__main__":
    debug_article()
