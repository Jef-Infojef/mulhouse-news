import psycopg2
import os
from dotenv import load_dotenv

load_dotenv(".env.local")
url = os.getenv("DATABASE_URL")

def list_tables():
    try:
        conn = psycopg2.connect(url)
        cur = conn.cursor()
        cur.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public';")
        tables = cur.fetchall()
        print("Tables dans Neon :")
        for t in tables:
            print(f"- {t[0]}")
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Erreur : {e}")

if __name__ == "__main__":
    list_tables()
