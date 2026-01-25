import requests
import re
import html

url = "https://www.alterpresse68.info/2025/12/16/la-dette-publique-instrument-de-domination-une-conference-de-patrick-saurin-a-mulhouse/"
headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}

try:
    print(f"Fetching {url}...")
    r = requests.get(url, headers=headers, timeout=10)
    print(f"Status: {r.status_code}")
    
    html_c = r.text
    
    # Chercher toutes les balises meta description
    metas = re.findall(r'<meta[^>]*description[^>]*>', html_c, re.IGNORECASE)
    print("\nBalises meta description trouvées :")
    for m in metas:
        print(m)

    # Essayer de trouver le premier paragraphe de contenu si pas de description
    # WordPress met souvent le contenu dans <div class="entry-content"> ou <article>
    p_content = re.search(r'<div class="entry-content"[^>]*>.*?<p>(.*?)</p>', html_c, re.DOTALL | re.IGNORECASE)
    if p_content:
        clean_p = re.sub(r'<[^>]+>', '', p_content.group(1)).strip()
        print(f"\nPremier paragraphe trouvé (fallback possible) : \n{clean_p[:200]}...")
    else:
        print("\nPas de 'entry-content' standard trouvé.")

except Exception as e:
    print(f"Erreur : {e}")
