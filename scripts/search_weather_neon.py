import psycopg2
import os
from dotenv import load_dotenv

# URL Neon
url = "postgresql://neondb_owner:npg_GX8cJA3bwtQO@ep-cool-mouse-agtxokbb-pooler.c-2.eu-central-1.aws.neon.tech/neondb?sslmode=require"

def search_everywhere():
    try:
        conn = psycopg2.connect(url)
        cur = conn.cursor()
        
        print("[*] Recherche de 'weather_history' sur NEON...")
        cur.execute("SELECT table_schema, table_name FROM information_schema.tables WHERE table_name LIKE '%weather%';")
        res = cur.fetchall()
        for s, t in res:
            print(f"✅ Trouvée : {s}.{t}")
            cur.execute(f'SELECT COUNT(*) FROM "{s}"."{t}"')
            print(f"   Nombre d'entrées : {cur.fetchone()[0]}")
            
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Erreur : {e}")

if __name__ == "__main__":
    search_everywhere()
