import requests

url = "https://www.bfmtv.com/alsace/replay-emissions/bonjour-l-alsace/video-on-a-rendez-vous-en-immersion-dans-la-banque-alimentaire-de-mulhouse_VN-202601230210.html"
headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}

try:
    r = requests.get(url, headers=headers)
    with open("debug_bfm.html", "w", encoding="utf-8") as f:
        f.write(r.text)
    print("Téléchargé.")
except Exception as e:
    print(f"Erreur: {e}")
