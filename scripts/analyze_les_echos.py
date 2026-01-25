import os
import psycopg2
from dotenv import load_dotenv
import requests

load_dotenv(".env.local")
DATABASE_URL = os.environ.get("NEWS_DATABASE_URL")

def analyze_les_echos():
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        
        # Récupérer un article Les Echos manquant
        cur.execute("""
            SELECT id, title, link
            FROM \"Article\" 
            WHERE source LIKE '%Echos%'
              AND ((\"imageUrl\" IS NULL OR \"imageUrl\" = '') OR (\"description\" IS NULL OR \"description\" = ''))
            LIMIT 1
        """)
        art = cur.fetchone()
        
        cur.close()
        conn.close()

        if art:
            print(f"ID: {art[0]}")
            print(f"Titre: {art[1]}")
            print(f"Lien: {art[2]}")
            
            # Test de fetching
            url = art[2]
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
            
            print(f"\nFetching {url}...")
            r = requests.get(url, headers=headers, timeout=10)
            print(f"Status: {r.status_code}")
            
            print("\nDébut du contenu reçu (500 chars) :")
            print(r.text[:500])
            
            if "datadome" in r.text.lower():
                print("\n[!] Détection possible de DataDome.")
            if "captcha" in r.text.lower():
                print("\n[!] Détection possible de CAPTCHA.")
            if "abonnement" in r.text.lower():
                print("\n[!] Contenu potentiellement réservé aux abonnés.")

        else:
            print("Aucun article Les Echos problématique trouvé.")

    except Exception as e:
        print(f"Erreur : {e}")

if __name__ == "__main__":
    analyze_les_echos()
