import requests
import re
from urllib.parse import urljoin

url = "https://www.mplusinfo.fr/"
print(f"[*] Scanning {url}...")

try:
    r = requests.get(url, timeout=10)
    # Chercher tous les liens
    links = re.findall(r'href=["\'](.*?)["\']', r.text)
    
    print("\n--- Liens PDF ou Magazine trouvés ---")
    found = False
    for link in links:
        if "pdf" in link.lower() or "magazine" in link.lower():
            full_link = urljoin(url, link)
            print(full_link)
            found = True
            
    if not found:
        print("Aucun lien direct trouvé. Le site utilise peut-être du chargement dynamique (JS).")

except Exception as e:
    print(f"Erreur: {e}")
