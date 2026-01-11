import requests
import re

url = "https://www.ouest-france.fr/meteo/grand-est/mulhouse-68100/la-meteo-du-jour-a-mulhouse-f3c53405-f446-4dca-ad31-59655c409210"
headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}

try:
    resp = requests.get(url, headers=headers, timeout=10)
    print(f"Status: {resp.status_code}")
    
    # Chercher spécifiquement og:image
    og_image = re.search(r'property=["\']og:image["\'][^>]*content=["\']([^"\\]+)["\']', resp.text)
    if og_image:
        print(f"OG Image : {og_image.group(1)}")
    else:
        # Pattern inverse
        og_image_v2 = re.search(r'content=["\']([^"\\]+)["\'][^>]*property=["\']og:image["\']', resp.text)
        if og_image_v2:
            print(f"OG Image (v2) : {og_image_v2.group(1)}")
        else:
            print("Aucune balise og:image trouvée.")
            
    # Vérifier s'il y a une protection
    if "protection" in resp.text.lower() or "challenge" in resp.text.lower():
        print("Détection d'une possible protection anti-robot.")

except Exception as e:
    print(f"Erreur : {e}")
