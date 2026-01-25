import os
import psycopg2
from dotenv import load_dotenv

def find_premium_candidates():
    root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    for f in [".envenv", ".env.local", ".env"]:
        if os.path.exists(f):
            load_dotenv(f)
            break
    
    url = os.environ.get("DATABASE_URL").replace("?pgbouncer=true", "")
    try:
        conn = psycopg2.connect(url)
        cur = conn.cursor()
        
        # On cherche des articles récents (Janvier 2026) sans contenu
        # Les articles premium n'ont souvent pas "Vidéo" ou "Diaporama" au début
        cur.execute("""
            SELECT title, link 
            FROM \"Article\" 
            WHERE source ILIKE '%%Alsace%%' 
              AND link LIKE '%%www.lalsace.fr%%'
              AND content IS NULL
            ORDER BY \"publishedAt\" DESC
            LIMIT 10
        """)
        articles = cur.fetchall()
        
        if articles:
            print("Candidats potentiels pour le test Premium :")
            for i, (title, link) in enumerate(articles, 1):
                print(f"{i}. {title}")
                print(f"   URL : {link}")
                print("-" * 20)
        else:
            print("Aucun article correspondant trouvé.")
            
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Erreur BDD: {e}")

if __name__ == "__main__":
    find_premium_candidates()

