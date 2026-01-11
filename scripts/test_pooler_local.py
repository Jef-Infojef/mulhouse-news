import psycopg2
import os
from dotenv import load_dotenv

# URL exacte du pooler transmise
url = "postgresql://postgres.wmvjpdedrfyttixdkzpi:05v0Ije8JayPNsaI@aws-1-eu-west-3.pooler.supabase.com:5432/postgres"

def test_conn():
    print(f"[*] Tentative de connexion LOCAL vers Pooler : {url.split('@')[-1]}...")
    try:
        conn = psycopg2.connect(url, connect_timeout=10)
        print("✅ Connexion réussie en LOCAL !")
        cur = conn.cursor()
        cur.execute("SELECT version();")
        print(f"Version : {cur.fetchone()[0]}")
        cur.close()
        conn.close()
    except Exception as e:
        print(f"❌ Échec de la connexion LOCAL : {e}")

if __name__ == "__main__":
    test_conn()
