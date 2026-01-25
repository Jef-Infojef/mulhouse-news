import os
import psycopg2
from dotenv import load_dotenv

def find_4kb_article():
    root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    for f in [".envenv", ".env.local", ".env"]:
        if os.path.exists(f):
            load_dotenv(f)
            break
    
    url = os.environ.get("DATABASE_URL").replace("?pgbouncer=true", "")
    try:
        conn = psycopg2.connect(url)
        cur = conn.cursor()
        
        # On cherche un article dont le contenu fait environ 4000 chars
        cur.execute("""
            SELECT title, link, LENGTH(content) as len
            FROM \"Article\" 
            WHERE source ILIKE '%%Alsace%%' 
              AND link LIKE '%%www.lalsace.fr%%'
              AND content IS NOT NULL
              AND LENGTH(content) BETWEEN 3800 AND 4500
            ORDER BY \"publishedAt\" DESC
            LIMIT 1
        """)
        res = cur.fetchone()
        
        if res:
            print(f"Titre : {res[0]}")
            print(f"URL : {res[1]}")
            print(f"Taille en base : {res[2]} caractères")
        else:
            print("Aucun article de cette taille trouvé.")
            
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Erreur BDD: {e}")

if __name__ == "__main__":
    find_4kb_article()
