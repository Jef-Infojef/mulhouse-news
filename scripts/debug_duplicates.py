import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()
DATABASE_URL = os.environ.get("DATABASE_URL")

def find_duplicates():
    try:
        url = DATABASE_URL
        if url and "DATABASE_URL=\"" in url:
            url = url.replace("DATABASE_URL=\"", "").replace("\"", "")
        if url and "?pgbouncer=true" in url:
            url = url.replace("?pgbouncer=true", "")
            
        conn = psycopg2.connect(url)
        cur = conn.cursor()
        
        # Chercher des titres identiques sur les 7 derniers jours
        query = """
            SELECT title, COUNT(*) 
            FROM \"Article\" 
            WHERE \"publishedAt\" > NOW() - INTERVAL '7 days'
            GROUP BY title 
            HAVING COUNT(*) > 1
            ORDER BY COUNT(*) DESC
            LIMIT 10;
        """
        
        cur.execute(query)
        duplicates = cur.fetchall()
        
        if not duplicates:
            print("Aucun doublon exact par titre trouvé sur les 7 derniers jours.")
        else:
            print("\n--- Doublons détectés par Titre ---")
            for title, count in duplicates:
                print(f"[{count} fois] {title}")
                
                # Voir les sources et liens pour ce titre
                cur.execute("SELECT source, link, \"publishedAt\" FROM \"Article\" WHERE title = %s ORDER BY \"publishedAt\" DESC", (title,))
                details = cur.fetchall()
                for source, link, pub in details:
                    print(f"   -> {source} | {pub} | {link[:60]}...")
                print("")

        cur.close()
        conn.close()
    except Exception as e:
        print(f"Erreur : {e}")

if __name__ == "__main__":
    find_duplicates()
