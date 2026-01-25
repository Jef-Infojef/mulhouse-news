import os
import psycopg2
from dotenv import load_dotenv

def check_article():
    root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    for f in [".envenv", ".env.local", ".env"]:
        if os.path.exists(f):
            load_dotenv(f)
            break
    
    url = os.environ.get("DATABASE_URL").replace("?pgbouncer=true", "")
    try:
        conn = psycopg2.connect(url)
        cur = conn.cursor()
        
        link = "https://mag.mulhouse-alsace.fr/evenement/animation-fievre-du-disco-a-la-patinoire-olympique-a-mulhouse-janvier-2026/"
        cur.execute('SELECT title, content, source FROM "Article" WHERE link = %s', (link,))
        res = cur.fetchone()
        
        if res:
            print(f"Titre : {res[0]}")
            print(f"Source : {res[2]}")
            print("\n=== CONTENU ===\n")
            print(res[1] if res[1] else "(NULL)")
            print("\n===============\n")
            if res[1]:
                print(f"Longueur : {len(res[1])} caractères")
        else:
            print("Article non trouvé dans la base de données.")
            
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Erreur BDD: {e}")

if __name__ == "__main__":
    check_article()
