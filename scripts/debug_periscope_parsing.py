import requests
import re
import html

url = "https://le-periscope.info/le-journal/photos-videos/ouverture-marche-de-noel-etoffeeries-de-mulhouse/"
headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}

try:
    print(f"Fetching {url}...")
    r = requests.get(url, headers=headers, timeout=10)
    html_c = r.text
    
    # 1. Chercher og:image
    og_img = re.search(r'property=["\']og:image["\'][^>]*content=["\']([^"\']+)["\']', html_c)
    if og_img:
        print(f"\n[OK] og:image trouvée : {html.unescape(og_img.group(1))}")
    else:
        print("\n[KO] Pas de og:image trouvée.")

    # 2. Chercher la première image du contenu
    # Souvent dans <div class="entry-content"> ou <div class="post-content">
    # On cherche <img ... src="...">
    print("\nRecherche d'images dans le contenu...")
    imgs = re.findall(r'<img[^>]+src=["\']([^"\']+)["\']', html_c)
    
    # Filtrer les petites icônes ou images non pertinentes
    valid_imgs = [img for img in imgs if not "logo" in img and not "icon" in img and (".jpg" in img or ".png" in img)]
    
    if valid_imgs:
        print("Images potentielles trouvées :")
        for img in valid_imgs[:5]: # Afficher les 5 premières
            print(f"- {html.unescape(img)}")
    else:
        print("Aucune image pertinente trouvée dans le contenu.")

except Exception as e:
    print(f"Erreur : {e}")
