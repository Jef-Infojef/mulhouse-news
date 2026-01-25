import requests

url = "https://actu.fr/grand-est/mulhouse_68224/marche-de-noel-de-mulhouse-2025-malgre-une-frequentation-en-baisse-de-27-la-ville-relativise-le-bilan_63734740.html"
headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}

try:
    r = requests.get(url, headers=headers)
    with open("debug_actufr.html", "w", encoding="utf-8") as f:
        f.write(r.text)
    print("Téléchargé.")
except Exception as e:
    print(f"Erreur: {e}")
