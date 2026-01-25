import requests
import re

url = "https://www.lalsace.fr/economie/2024/01/09/a-l-illberg-le-plus-gros-reservoir"
headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}

try:
    print(f"Fetching {url}...")
    r = requests.get(url, headers=headers, timeout=10)
    print(f"Status: {r.status_code}")
    
    html_c = r.text
    
    # Chercher toutes les balises meta description pour voir ce qui existe
    metas = re.findall(r'<meta[^>]*description[^>]*>', html_c, re.IGNORECASE)
    print("\nBalises meta description trouvées :")
    for m in metas:
        print(m)

    # Test de ma regex actuelle
    print("\nTest Regex actuelle :")
    m_desc = re.search(r'property=["\']og:description["\'][^>]*content=["\']([^"\\]+)["\']', html_c)
    if not m_desc:
        print("og:description non trouvé (méthode 1)")
        m_desc = re.search(r'name=["\']description["\'][^>]*content=["\']([^"\\]+)["\']', html_c)
    
    if m_desc:
        print(f"Trouvé : {m_desc.group(1)}")
    else:
        print("Rien trouvé avec les regex actuelles.")

except Exception as e:
    print(f"Erreur : {e}")
