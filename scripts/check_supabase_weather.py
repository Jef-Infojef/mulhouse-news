import psycopg2
import os
from dotenv import load_dotenv

load_dotenv(".env.local")
url = "postgresql://postgres.wmvjpdedrfyttixdkzpi:05v0Ije8JayPNsaI@aws-1-eu-west-3.pooler.supabase.com:5432/postgres"

def check_weather():
    print(f"[*] Vérification de weather_history sur Supabase...")
    try:
        conn = psycopg2.connect(url)
        cur = conn.cursor()
        cur.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public';")
        tables = cur.fetchall()
        print("Tables dans Supabase :")
        for t in tables:
            print(f"- {t[0]}")
            
        cur.execute("SELECT COUNT(*) FROM weather_history;")
        count = cur.fetchone()[0]
        print(f"✅ Table trouvée ! Nombre d'entrées : {count}")
        
        cur.close()
        conn.close()
    except Exception as e:
        print(f"❌ Erreur : {e}")

if __name__ == "__main__":
    check_weather()
