import requests
import re

url = "https://www.alterpresse68.info/2026/01/10/a-mulhouse-quand-la-grande-ambition-dune-figure-politique-italienne-contraste-avec-la-grande-confusion-ideologique-occidentale-actuelle/"
headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}

try:
    resp = requests.get(url, headers=headers, timeout=10)
    print(f"Status: {resp.status_code}")
    # Chercher toutes les balises meta image
    metas = re.findall(r'<meta[^>]+>', resp.text)
    for m in metas:
        if 'image' in m.lower():
            print(f"Meta trouvée : {m}")
            
    # Chercher spécifiquement og:image
    og_image = re.search(r'property=["\']og:image["\'][^>]*content=["\']([^"\\]+)["\']', resp.text)
    if og_image:
        print(f"OG Image (Pattern 1) : {og_image.group(1)}")
    else:
        og_image_v2 = re.search(r'content=["\']([^"\\]+)["\'][^>]*property=["\']og:image["\']', resp.text)
        if og_image_v2:
            print(f"OG Image (Pattern 2) : {og_image_v2.group(1)}")
        else:
            print("Aucune balise og:image trouvée avec les patterns actuels.")

except Exception as e:
    print(f"Erreur : {e}")
