import os
import requests
from bs4 import BeautifulSoup

COOKIES_RAW = ".XCONNECT_SESSION=2=42F647DB9B788CF4E0AFFF1DD52DE98DAC09560B7B8173B6AE707DE13249B5D3D98E26C37209690D989A05961C1E93CBDDF2909ED6FF95194BEA6AE2C1E5A62F519DB83384CA795ACE1E2824AA4C1D00C904F51699D03E6489E9A4B4C8211E0D25B9B66E68555AA3B098E18D1CFB0D8E55CD162A101CF8E23306F0A225ABBE4E6AA1480CEA97DAEF016F99185FECA69B74DCE53DE2A59FB8889A43374A7891008D274391E153481FAF94E8CF51E25A9872DE0D0AA146142A059E319D5BEC9708926A8C25B1A97FBA849A2B64CC973B6CE3700E3E16AB420B9135DE775FE8D9E4AF4D143969441F03400814963FB3C265; .XCONNECTKeepAlive=2=1; .XCONNECT=2=1; _poool=9aab6ee3-fda6-43fc-a90e-29de3c73d8f7"

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

def analyze_video():
    url = "https://www.lalsace.fr/videos/mulhouse-on-a-visite-la-librairie-bisey-metamorphosee-3qrku8r"
    session = requests.Session()
    session.headers.update(headers)
    for key, value in cookies.items():
        session.cookies.set(key, value, domain=".lalsace.fr")

    try:
        print(f"[*] Chargement de la page (connecté)...")
        response = session.get(url, timeout=15)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Sauvegarde pour inspection manuelle si besoin
        with open("debug_video_connected.html", "w", encoding="utf-8") as f:
            f.write(response.text)

        # Recherche du texte fourni par l'utilisateur
        target = "Adopte une étagère"
        found = False
        print(f"[*] Recherche de '{target}'...")
        
        for tag in soup.find_all(True): # Parcourt toutes les balises
            if target in tag.get_text():
                # On cherche la balise la plus profonde qui contient le texte
                if not tag.find(True, string=lambda s: s and target in s):
                    print(f"   ✅ Trouvé dans la balise : <{tag.name} class='{tag.get('class')}'>")
                    print(f"   📝 Contenu : {tag.get_text()[:200]}...")
                    found = True
                    break
        
        if not found:
            print("   ❌ Texte non trouvé dans le HTML (même connecté)")
            # Vérification LD+JSON
            import json
            for s in soup.find_all('script', type='application/ld+json'):
                try:
                    data = json.loads(s.string)
                    # Si c'est une liste
                    if isinstance(data, list):
                        for item in data:
                            if 'description' in item and target in item['description']:
                                print("   ✅ Trouvé dans un bloc SCRIPT application/ld+json !")
                                print(f"   📝 Description : {item['description'][:200]}...")
                    elif 'description' in data and target in data['description']:
                        print("   ✅ Trouvé dans un bloc SCRIPT application/ld+json !")
                        print(f"   📝 Description : {data['description'][:200]}...")
                except: pass

    except Exception as e:
        print(f"❌ Erreur : {e}")

if __name__ == "__main__":
    analyze_video()