import psycopg2
import os
from dotenv import load_dotenv

load_dotenv(".env.local")
url = os.getenv("DATABASE_URL")

def list_all():
    try:
        conn = psycopg2.connect(url)
        cur = conn.cursor()
        print("[*] Schémas disponibles :")
        cur.execute("SELECT schema_name FROM information_schema.schemata;")
        for s in cur.fetchall():
            print(f"  - {s[0]}")
            
        print("\n[*] Toutes les tables :")
        cur.execute("SELECT table_schema, table_name FROM information_schema.tables WHERE table_schema NOT IN ('information_schema', 'pg_catalog');")
        for t in cur.fetchall():
            print(f"  - {t[0]}.{t[1]}")
            
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Erreur : {e}")

if __name__ == "__main__":
    list_all()

