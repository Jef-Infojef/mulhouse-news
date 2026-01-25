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
                COUNT(*) FILTER (WHERE LENGTH(content) < 500) as short
            FROM "Article" 
            WHERE source ILIKE '%Alsace%' 
              AND "publishedAt" >= '2025-12-01' 
              AND "publishedAt" < '2026-01-01'
        """)
        total, completed, short = cur.fetchone()
        
        print(f"L'Alsace - Décembre 2025 :")
        print(f" - Total articles : {total}")
        print(f" - Articles complétés : {completed}")
        print(f" - Articles sans contenu : {total - completed}")
        print(f" - Articles complétés < 500 chars : {short}")
        
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Erreur BDD: {e}")

if __name__ == "__main__":
    get_count()
