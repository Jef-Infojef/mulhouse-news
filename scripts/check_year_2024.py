import os
import psycopg2
from dotenv import load_dotenv

def check_year_2024():
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
              AND link LIKE '%%www.lalsace.fr%%'
              AND \"publishedAt\" >= '2024-01-01' 
              AND \"publishedAt\" < '2025-01-01'
        """)
        total, completed = cur.fetchone()
        
        print(f"L'Alsace - Année 2024 :")
        print(f" - Total articles : {total}")
        print(f" - Articles complétés : {completed}")
        print(f" - Articles à scraper : {total - completed}")
        
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Erreur BDD: {e}")

if __name__ == "__main__":
    check_year_2024()

