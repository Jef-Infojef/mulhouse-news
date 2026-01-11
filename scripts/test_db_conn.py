import psycopg2
import os
from dotenv import load_dotenv

load_dotenv(".env.local")
url = os.getenv("NEWS_DATABASE_URL").replace(":5432/", ":6543/")

def test_conn():
    print(f"[*] Tentative de connexion à : {url.split('@')[-1] if url else 'URL manquante'}...")
    try:
        conn = psycopg2.connect(url, connect_timeout=10)
        print("✅ Connexion réussie !")
        cur = conn.cursor()
        cur.execute("SELECT version();")
        print(f"Version : {cur.fetchone()[0]}")
        cur.close()
        conn.close()
    except Exception as e:
        print(f"❌ Échec de la connexion : {e}")

if __name__ == "__main__":
    test_conn()
