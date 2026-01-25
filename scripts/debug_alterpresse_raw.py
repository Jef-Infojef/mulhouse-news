import requests

url = "https://www.alterpresse68.info/2025/12/16/la-dette-publique-instrument-de-domination-une-conference-de-patrick-saurin-a-mulhouse/"
headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}

try:
    r = requests.get(url, headers=headers, timeout=10)
    print(f"Status: {r.status_code}")
    print("\nDébut du contenu reçu :")
    print(r.text[:1000])

except Exception as e:
    print(f"Erreur : {e}")

