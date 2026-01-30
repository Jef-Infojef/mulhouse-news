import requests
import os
import zipfile
import io
from dotenv import load_dotenv

load_dotenv(".env.local")
token = os.getenv("GITHUB_TOKEN")
repo = "Jef-Infojef/mulhouse-news"
run_id = "20885143306"

def fetch_logs():
    if not token:
        print("Erreur : GITHUB_TOKEN manquant.")
        return

    url = f"https://api.github.com/repos/{repo}/actions/runs/{run_id}/logs"
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json"
    }

    print(f"[*] Téléchargement des logs pour le run {run_id}...")
    response = requests.get(url, headers=headers, allow_redirects=True)
    
    if response.status_code != 200:
        print(f"Erreur lors du téléchargement: {response.status_code}")
        return

    # Extraire le zip en mémoire
    with zipfile.ZipFile(io.BytesIO(response.content)) as z:
        # Chercher le fichier log du job "scrape"
        log_files = [f for f in z.namelist() if "scrape" in f.lower() and f.endswith(".txt")]
        if not log_files:
            # Si pas trouvé, lister tout
            log_files = [f for f in z.namelist() if f.endswith(".txt")]

        if log_files:
            # On prend le plus gros ou le premier pertinent
            log_file = log_files[0]
            print(f"[*] Lecture du fichier : {log_file}\n")
            with z.open(log_file) as f:
                content = f.read().decode('utf-8', errors='ignore')
                
                # On cherche les lignes du script python
                lines = content.splitlines()
                # On filtre pour voir ce qui nous intéresse (les logs de notre script)
                for line in lines:
                    if "Traitement:" in line or "[!" in line or "Échec décodage:" in line or "URL:" in line:
                        print(line)
        else:
            print("Aucun fichier log trouvé dans le zip.")

if __name__ == "__main__":
    fetch_logs()
