import os
import psycopg2
from dotenv import load_dotenv

def get_count():
    root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    for f in [".envenv", ".env.local", ".env"]:
        path = os.path.join(root_dir, f)
        if os.path.exists(path):
            load_dotenv(path)
            break
    
    url = os.environ.get("DATABASE_URL").replace("?pgbouncer=true", "")
    try:
        conn = psycopg2.connect(url)
        cur = conn.cursor()
        
        cur.execute("""
            SELECT 
                COUNT(*) as total,
                COUNT(content) as completed,
                COUNT(*) FILTER (WHERE LENGTH(content) < 200) as very_short
            FROM \"Article\" 
            WHERE source ILIKE '%%Alsace%%' 
              AND \"publishedAt\" >= '2026-01-01' 
              AND \"publishedAt\" < '2026-02-01'
        """)
        total, completed, very_short = cur.fetchone()
        
        print(f"L'Alsace - Janvier 2026 :")
        print(f" - Total articles : {total}")
        print(f" - Articles complétés : {completed}")
        print(f" - Articles sans contenu : {total - completed}")
        if completed > 0:
            print(f" - Articles < 200 chars : {very_short}")
        
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Erreur BDD: {e}")

if __name__ == "__main__":
    get_count()
