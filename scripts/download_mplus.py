import requests

url = "https://mag.mulhouse-alsace.fr/evenement/hamlet-a-la-filature-a-mulhouse-2026/"
headers = {'User-Agent': 'Mozilla/5.0'}

try:
    r = requests.get(url, headers=headers)
    with open("debug_mplus.html", "w", encoding="utf-8") as f:
        f.write(r.text)
    print("Téléchargé.")
except Exception as e:
    print(f"Erreur: {e}")
