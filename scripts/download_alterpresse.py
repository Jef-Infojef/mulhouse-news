import requests

url = "https://www.alterpresse68.info/2026/01/24/massif-du-sprickelsberg-pres-de-mulhouse-la-cour-administrative-dappel-se-prononce-contre-une-vision-purement-extractiviste-de-la-foret/"
headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}

try:
    r = requests.get(url, headers=headers)
    with open("debug_alterpresse.html", "w", encoding="utf-8") as f:
        f.write(r.text)
    print("Téléchargé.")
except Exception as e:
    print(f"Erreur: {e}")
