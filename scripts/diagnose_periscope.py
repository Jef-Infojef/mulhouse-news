import os
import psycopg2
from dotenv import load_dotenv

load_dotenv(".env.local")
DATABASE_URL = os.environ.get("NEWS_DATABASE_URL")

def diagnose_periscope():
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        
        # Récupérer un article Le Periscope avec image manquante
        cur.execute("""
            SELECT id, title, link, "imageUrl", "description"
            FROM "Article" 
            WHERE (source LIKE '%Périscope%' OR link LIKE '%le-periscope.info%')
              AND ("imageUrl" IS NULL OR "imageUrl" = '')
            LIMIT 1
        """)
        art = cur.fetchone()
        
        if art:
            print(f"ID: {art[0]}")
            print(f"Titre: {art[1]}")
            print(f"Lien: {art[2]}")
            
            # Sauvegarder l'URL
            with open("periscope_url.txt", "w") as f:
                f.write(art[2])
        else:
            print("Aucun article Le Periscope avec image manquante trouvé.")

        cur.close()
        conn.close()
    except Exception as e:
        print(f"Erreur : {e}")

if __name__ == "__main__":
    diagnose_periscope()
