import requests

url = "https://www.francebleu.fr/infos/faits-divers-justice/mulhouse-55-kilos-de-cigarettes-saisies-par-les-douanes-un-epicier-interpelle-9432807"
headers = {'User-Agent': 'Mozilla/5.0'}

try:
    r = requests.get(url, headers=headers)
    with open("debug_francebleu.html", "w", encoding="utf-8") as f:
        f.write(r.text)
    print("Téléchargé.")
except Exception as e:
    print(f"Erreur: {e}")
