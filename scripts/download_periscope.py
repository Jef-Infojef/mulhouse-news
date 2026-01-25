import requests

url = "https://le-periscope.info/le-journal/actualites/cafe-guillaume-tell-une-adresse-emblematique-de-mulhouse/"
headers = {'User-Agent': 'Mozilla/5.0'}

try:
    r = requests.get(url, headers=headers)
    with open("debug_periscope.html", "w", encoding="utf-8") as f:
        f.write(r.text)
    print("Téléchargé.")
except Exception as e:
    print(f"Erreur: {e}")
