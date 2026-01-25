import os
import psycopg2
from dotenv import load_dotenv

def get_count():
    # Chargement de l'env
    env_files = [".envenv", ".env.local", ".env"]
    found = False
    for f in env_files:
        if os.path.exists(f):
            load_dotenv(f)
            if os.environ.get("DATABASE_URL"):
                found = True
                break
    
    if not found:
        print("Erreur: DATABASE_URL non trouvée.")
        return

    url = os.environ.get("DATABASE_URL").replace("?pgbouncer=true", "")
    try:
        conn = psycopg2.connect(url)
        cur = conn.cursor()
        
        # Nombre total d'articles
        cur.execute("""
            SELECT COUNT(*) 
            FROM \"Article\" 
            WHERE source ILIKE '%%Alsace%%' 
              AND \"publishedAt\" >= '2025-10-01' 
              AND \"publishedAt\" < '2025-11-01'
        """)
        total = cur.fetchone()[0]
        
        # Nombre d'articles sans contenu
        cur.execute("""
            SELECT COUNT(*) 
            FROM \"Article\" 
            WHERE source ILIKE '%%Alsace%%' 
              AND content IS NULL
              AND \"publishedAt\" >= '2025-10-01' 
              AND \"publishedAt\" < '2025-11-01'
        """)
        missing = cur.fetchone()[0]
        
        print(f"Total articles L'Alsace (Oct 2025) : {total}")
        print(f"Articles sans contenu : {missing}")
        print(f"Articles déjà complétés : {total - missing}")
        
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Erreur BDD: {e}")

if __name__ == "__main__":
    get_count()
