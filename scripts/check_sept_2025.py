import os
import psycopg2
from dotenv import load_dotenv

def get_count():
    root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    for f in [".envenv", ".env.local", ".env"]:
        if os.path.exists(f):
            load_dotenv(f)
            break
    
    url = os.environ.get("DATABASE_URL").replace("?pgbouncer=true", "")
    try:
        conn = psycopg2.connect(url)
        cur = conn.cursor()
        
        cur.execute("""
            SELECT 
                COUNT(*) as total,
                COUNT(content) as completed
            FROM \"Article\" 
            WHERE source ILIKE '%%Alsace%%' 
              AND \"publishedAt\" >= '2025-09-01' 
              AND \"publishedAt\" < '2025-10-01'
        """)
        total, completed = cur.fetchone()
        
        print(f"L'Alsace - Septembre 2025 :")
        print(f" - Total articles : {total}")
        print(f" - Articles complétés : {completed}")
        print(f" - Articles sans contenu : {total - completed}")
        
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Erreur BDD: {e}")

if __name__ == "__main__":
    get_count()
