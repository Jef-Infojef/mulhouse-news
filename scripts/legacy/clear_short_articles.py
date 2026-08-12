import os
import psycopg2
from dotenv import load_dotenv

def clear_short_articles():
    # Chargement de l'environnement
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
    
    if not found:
        print("Erreur: DATABASE_URL non trouvée.")
        return

    url = os.environ.get("DATABASE_URL").replace("?pgbouncer=true", "")
    try:
        conn = psycopg2.connect(url)
        cur = conn.cursor()
        
        # Sélection des articles de L'Alsace en Septembre 2025 avec contenu
        query_select = """
            SELECT id, title, LENGTH(content) 
            FROM \"Article\" 
            WHERE source ILIKE '%%Alsace%%' 
              AND content IS NOT NULL
              AND \"publishedAt\" >= '2025-09-01' 
              AND \"publishedAt\" < '2025-10-01'
        """
        cur.execute(query_select)
        to_clear = cur.fetchall()
        
        if not to_clear:
            print("Aucun article de moins de 1000 caractères trouvé.")
            return

        print(f"Trouvé {len(to_clear)} articles dont le contenu sera effacé (remis à NULL) :")
        for art in to_clear:
            print(f" - {art[1][:50]}... ({art[2]} chars)")

        # Mise à NULL du contenu
        ids = tuple(art[0] for art in to_clear)
        query_update = 'UPDATE "Article" SET content = NULL WHERE id IN %s'
        cur.execute(query_update, (ids,))
        
        conn.commit()
        print(f"\n✅ Terminé. {len(to_clear)} contenus ont été effacés. Ils seront repris par le prochain passage du scraper.")
        
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Erreur BDD: {e}")

if __name__ == "__main__":
    clear_short_articles()
