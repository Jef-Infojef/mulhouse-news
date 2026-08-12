import os
import psycopg2
from dotenv import load_dotenv

def get_stats():
    root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    env_files = [".envenv", ".env.local", ".env"]
    found = False
    for f in env_files:
        path = os.path.join(root_dir, f)
        if os.path.exists(path):
            load_dotenv(path)
            if os.environ.get("DATABASE_URL"):
                found = True
                break
    
    if not found: return

    url = os.environ.get("DATABASE_URL").replace("?pgbouncer=true", "")
    try:
        conn = psycopg2.connect(url)
        cur = conn.cursor()
        
        cur.execute("""
            SELECT 
                AVG(LENGTH(content)) as avg_len,
                MIN(LENGTH(content)) as min_len,
                MAX(LENGTH(content)) as max_len,
                COUNT(*) as count,
                COUNT(*) FILTER (WHERE LENGTH(content) < 1000) as short_count
            FROM \"Article\" 
            WHERE source ILIKE '%%Alsace%%' 
              AND content IS NOT NULL
              AND \"publishedAt\" >= '2025-11-01' 
              AND \"publishedAt\" < '2025-12-01'
        """)
        stats = cur.fetchone()
        
        print(f"Statistiques L'Alsace - Novembre 2025 (Complétés) :")
        print(f" - Nombre d'articles : {stats[3]}")
        print(f" - Taille moyenne : {int(stats[0]) if stats[0] else 0} caractères")
        print(f" - Taille min : {stats[1] if stats[1] else 0} caractères")
        print(f" - Taille max : {stats[2] if stats[2] else 0} caractères")
        print(f" - Articles < 1000 chars : {stats[4]}")
        
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Erreur BDD: {e}")

if __name__ == "__main__":
    get_stats()
