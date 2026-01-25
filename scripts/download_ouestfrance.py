import requests

url = "https://www.ouest-france.fr/meteo/grand-est/mulhouse-68100/la-meteo-du-jour-a-mulhouse-3333b8ad-4ea8-47bf-8d76-031ec2cf0d07"
headers = {'User-Agent': 'Mozilla/5.0'}

try:
    r = requests.get(url, headers=headers)
    with open("debug_ouestfrance.html", "w", encoding="utf-8") as f:
        f.write(r.text)
    print("Téléchargé.")
except Exception as e:
    print(f"Erreur: {e}")
