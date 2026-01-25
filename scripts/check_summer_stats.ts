import os
import psycopg2
from dotenv import load_dotenv

def get_count():
    root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    for f in ["..env", ".env.local", ".env"]:
        path = os.path.join(root_dir, f)
        if os.path.exists(path):
            load_dotenv(path)
            break
    
    url = os.environ.get("DATABASE_URL").replace("?pgbouncer=true", "")
    try:
        conn = psycopg2.connect(url)
        cur = conn.cursor()
        
        for month, start, end in [("Juillet", "2025-07-01", "2025-08-01"), ("Août", "2025-08-01", "2025-09-01")]:
            cur.execute(f"""
                SELECT 
                    COUNT(*) as total,
                    COUNT(content) as completed,
                    COUNT(*) FILTER (WHERE LENGTH(content) < 500) as short
                FROM \"Article\" 
                WHERE source ILIKE '%%Alsace%%' 
                  AND \"publishedAt\" >= '{start}' 
                  AND \"publishedAt\" < '{end}'
            """)
            total, completed, short = cur.fetchone()
            
            print(f"L'Alsace - {month} 2025 :")
            print(f" - Total articles : {total}")
            print(f" - Articles complétés : {completed}")
            print(f" - Articles sans contenu : {total - completed}")
            print(f" - Articles complétés < 500 chars : {short}")
            print("-" * 30)
        
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Erreur BDD: {e}")

if __name__ == "__main__":
    get_count()