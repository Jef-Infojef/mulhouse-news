import os
import psycopg2
from dotenv import load_dotenv

def get_failed_link():
    root_dir = os.getcwd()
    for f in ["..envenv", ".env.local", ".env"]:
        if os.path.exists(f):
            load_dotenv(f)
            break
    
    url = os.environ.get("DATABASE_URL").replace("?pgbouncer=true", "")
    try:
        conn = psycopg2.connect(url)
        cur = conn.cursor()
        
        cur.execute("""
            SELECT link, title 
            FROM \"Article\" 
            WHERE source ILIKE '%Alsace%' 
              AND content IS NULL 
              AND link NOT ILIKE '%mag.mulhouse-alsace.fr%' 
              AND \"publishedAt\" >= '2025-09-01' 
              AND \"publishedAt\" < '2025-10-01' 
            ORDER BY \"publishedAt\" DESC 
            LIMIT 1
        """)
        res = cur.fetchone()
        if res:
            print(f"Lien : {res[0]}")
            print(f"Titre : {res[1]}")
        
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Erreur BDD: {e}")

if __name__ == "__main__":
    get_failed_link()

