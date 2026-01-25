import requests
import re

url = "https://www.alterpresse68.info/2025/12/16/la-dette-publique-instrument-de-domination-une-conference-de-patrick-saurin-a-mulhouse/"
headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}

try:
    print(f"Fetching {url}...")
    r = requests.get(url, headers=headers, timeout=10)
    
    html_c = r.text
    
    # Chercher où commence le contenu visible
    # On cherche une occurrence d'un mot du titre pour se repérer
    pos = html_c.find("Patrick Saurin")
    if pos != -1:
        print("\nContexte autour de 'Patrick Saurin' :")
        print(html_c[pos-500:pos+1000]) # 500 chars avant, 1000 après
    else:
        print("Mot clé non trouvé dans le HTML.")

except Exception as e:
    print(f"Erreur : {e}")

