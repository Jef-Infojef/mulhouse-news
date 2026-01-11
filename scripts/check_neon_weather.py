import psycopg2
import os
from dotenv import load_dotenv

load_dotenv(".env.local")
url = os.getenv("DATABASE_URL")

def check_weather():
    print(f"[*] Vérification de weather_history sur Neon...")
    try:
        conn = psycopg2.connect(url)
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM weather_history;")
        count = cur.fetchone()[0]
        print(f"✅ Table trouvée ! Nombre d'entrées : {count}")
        
        cur.execute("SELECT * FROM weather_history LIMIT 5;")
        rows = cur.fetchall()
        for row in rows:
            print(row)
            
        cur.close()
        conn.close()
    except Exception as e:
        print(f"❌ Erreur ou table non trouvée : {e}")

if __name__ == "__main__":
    check_weather()
