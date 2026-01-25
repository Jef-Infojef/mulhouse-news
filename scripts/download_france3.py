import requests

url = "https://france3-regions.franceinfo.fr/grand-est/haut-rhin/mulhouse/dans-les-coulisses-du-tramway-de-mulhouse-20-ans-apres-sa-mise-en-service-3278213.html"
headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}

try:
    r = requests.get(url, headers=headers)
    with open("debug_france3.html", "w", encoding="utf-8") as f:
        f.write(r.text)
    print("Téléchargé.")
except Exception as e:
    print(f"Erreur: {e}")
