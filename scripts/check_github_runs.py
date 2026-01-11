import requests
import os
from dotenv import load_dotenv
from datetime import datetime

load_dotenv(".env.local")
token = os.getenv("GITHUB_TOKEN")
repo = "Jef-Infojef/mulhouse-news"

def check_github_actions():
    if not token:
        print("Erreur : GITHUB_TOKEN non trouvé dans .env.local")
        return

    url = f"https://api.github.com/repos/{repo}/actions/runs"
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json"
    }

    try:
        response = requests.get(url, headers=headers)
        data = response.json()
        
        runs = data.get("workflow_runs", [])
        print(f"--- 10 dernières exécutions de GitHub Actions pour {repo} ---")
        for run in runs[:10]:
            created_at = run.get("created_at")
            status = run.get("status")
            conclusion = run.get("conclusion")
            name = run.get("name")
            
            # Formatage de la date
            dt = datetime.strptime(created_at, "%Y-%m-%dT%H:%M:%SZ")
            local_time = dt.strftime("%d/%m/%Y %H:%M:%S")
            
            print(f"[{local_time}] {name} (ID: {run.get('id')})")
            print(f"    Statut: {status} | Conclusion: {conclusion}")
            print("-" * 30)
            
    except Exception as e:
        print(f"Erreur lors de la requête API: {e}")

if __name__ == "__main__":
    check_github_actions()
