import os
import psycopg2
from dotenv import load_dotenv

def check_images():
    root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    for f in ["..envenv", ".env.local", ".env"]:
        if os.path.exists(f):
            load_dotenv(f)
            break
    
    url = os.environ.get("DATABASE_URL").replace("?pgbouncer=true", "")
    try:
        conn = psycopg2.connect(url)
        cur = conn.cursor()
        
        cur.execute("SELECT COUNT(*) FROM \"Article\" WHERE \"imageUrl\" IS NULL OR \"imageUrl\" = ''")
        missing = cur.fetchone()[0]
        
        cur.execute("SELECT COUNT(*) FROM \"Article\"")
        total = cur.fetchone()[0]
        
        print(f"Total articles : {total}")
        print(f"Articles sans image : {missing}")
        print(f"Taux de complétion images : {((total - missing) / total * 100):.1f}%")
        
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Erreur BDD: {e}")

if __name__ == "__main__":
    check_images()