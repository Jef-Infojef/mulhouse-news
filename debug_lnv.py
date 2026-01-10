import requests
import re

url = "https://www.lnv.fr/actualites/2026-01-05/montpellier-et-mulhouse-la-belle-affaire"
headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}

try:
    print(f"Fetching {url}...")
    resp = requests.get(url, headers=headers, timeout=10)
    print(f"Status Code: {resp.status_code}")
    
    if resp.status_code == 200:
        print("Searching for og:image...")
        
        # Pattern 1
        match1 = re.search(r'<meta\s+[^>]*property=["\']og:image["\'][^>]*content=["\']([^"\\]+)["\\]', resp.text, re.IGNORECASE)
        # Pattern 2
        match2 = re.search(r'<meta\s+[^>]*content=["\']([^"\\]+)["\\][^>]*property=["\']og:image["\\]', resp.text, re.IGNORECASE)
        
        if match1:
            print(f"FOUND (Pattern 1): {match1.group(1)}")
        elif match2:
             print(f"FOUND (Pattern 2): {match2.group(1)}")
        else:
            print("NOT FOUND with standard patterns.")
            
            # Recherche large pour voir ce qui existe
            loose_matches = re.findall(r'(image|img|src|content)=["\']([^"\\]+\.(jpg|jpeg|png|webp))["\\]', resp.text, re.IGNORECASE)
            print(f"Potential images found in source ({len(loose_matches)}):")
            for i, m in enumerate(loose_matches[:5]):
                print(f" - {m[1]}")

except Exception as e:
    print(f"Error: {e}")
