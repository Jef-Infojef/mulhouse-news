import requests
from bs4 import BeautifulSoup

# Configuration
COOKIES_RAW = ".XCONNECT_SESSION=2=42F647DB9B788CF4E0AFFF1DD52DE98DAC09560B7B8173B6AE707DE13249B5D3D98E26C37209690D989A05961C1E93CBDDF2909ED6FF95194BEA6AE2C1E5A62F519DB83384CA795ACE1E2824AA4C1D00C904F51699D03E6489E9A4B4C8211E0D25B9B66E68555AA3B098E18D1CFB0D8E55CD162A101CF8E23306F0A225ABBE4E6AA1480CEA97DAEF016F99185FECA69B74DCE53DE2A59FB8889A43374A7891008D274391E153481FAF94E8CF51E25A9872DE0D0AA146142A059E319D5BEC9708926A8C25B1A97FBA849A2B64CC973B6CE3700E3E16AB420B9135DE775FE8D9E4AF4D143969441F03400814963FB3C265; .XCONNECTKeepAlive=2=1; .XCONNECT=2=1; _poool=9aab6ee3-fda6-43fc-a90e-29de3c73d8f7"

# Parsing du cookie
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

def check_lalsace():
    print("[*] Test de connexion à L'Alsace...")
    url = "https://www.lalsace.fr/"
    
    try:
        response = requests.get(url, headers=headers, cookies=cookies, timeout=15)
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Recherche d'indices de connexion
            page_text = response.text.lower()
            
            indicators = [
                "se déconnecter",
                "mon compte",
                "mon profil",
                "connect-link",
                "user-name"
            ]
            
            found = [ind for ind in indicators if ind in page_text]
            
            if found:
                print(f"   ✅ CONNECTÉ ! (Indices trouvés: {', '.join(found)})")
            else:
                print("   ❌ NON CONNECTÉ (Page chargée mais aucun profil détecté)")
                # Vérifions s'il y a un bouton de connexion
                if "se connecter" in page_text:
                    print("   ℹ️ Le bouton 'Se connecter' est visible.")
        
        elif response.status_code == 403:
            print("   ❌ ERREUR 403: Accès refusé par le serveur (Bot détecté ou IP bloquée)")
        else:
            print(f"   ❌ ERREUR {response.status_code}: Impossible de charger la page")

    except Exception as e:
        print(f"   ❌ ERREUR: {e}")

if __name__ == "__main__":
    check_lalsace()
