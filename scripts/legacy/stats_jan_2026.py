import os
import psycopg2
from dotenv import load_dotenv

def get_stats():
    root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    for f in ["..env", ".env.local", ".env"]:
        if os.path.exists(f):
            load_dotenv(f)
            break
    
    url = os.environ.get("DATABASE_URL").replace("?pgbouncer=true", "")
    try:
        conn = psycopg2.connect(url)
        cur = conn.cursor()
        
        cur.execute("""
            SELECT 
                COUNT(*) FILTER (WHERE LENGTH(content) < 500) as under_500,
                COUNT(*) FILTER (WHERE LENGTH(content) >= 500 AND LENGTH(content) < 1000) as between_500_1000,
                COUNT(*) FILTER (WHERE LENGTH(content) >= 1000) as over_1000,
                AVG(LENGTH(content)) as avg_len
            FROM \"Article\" 
            WHERE source ILIKE '%%Alsace%%' 
              AND content IS NOT NULL
              AND \"publishedAt\" >= '2026-01-01' 
              AND \"publishedAt\" < '2026-02-01'
        """)
        stats = cur.fetchone()
        
        print(f"Tailles L'Alsace - Janvier 2026 :")
        print(f" - < 500 chars : {stats[0]}")
        print(f" - 500-1000 chars : {stats[1]}")
        print(f" - > 1000 chars : {stats[2]}")
        print(f" - Taille moyenne : {int(stats[3]) if stats[3] else 0} caractères")
        
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Erreur BDD: {e}")

if __name__ == "__main__":
    get_stats()
