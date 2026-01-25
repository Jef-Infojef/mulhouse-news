import os
import psycopg2
from dotenv import load_dotenv

load_dotenv(".env.local")
DATABASE_URL = os.environ.get("NEWS_DATABASE_URL")

def force_fix_ebra():
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        
        print("[*] Tentative de correction forcée pour les articles EBRA vides...")
        
        # Sélectionner les articles EBRA avec description vide
        cur.execute("""
            SELECT id, title, source
            FROM \"Article\" 
            WHERE (source LIKE '%Alsace%' OR source LIKE '%DNA%')
              AND ("description" IS NULL OR "description" = '')
        """)
        articles = cur.fetchall()
        
        print(f"[*] {len(articles)} articles trouvés.")
        
        fixed = 0
        for art_id, title, source in articles:
            # On utilise le titre comme description de secours
            fallback_desc = title
            
            cur.execute("""
                UPDATE \"Article\" 
                SET \"description\" = %s 
                WHERE id = %s
            """, (fallback_desc, art_id))
            
            fixed += 1
            print(f"   [Fixed] {title[:30]}... -> Description = Titre")
            
        conn.commit()
        cur.close()
        conn.close()
        print(f"\n✅ {fixed} articles mis à jour avec le titre comme description.")

    except Exception as e:
        print(f"Erreur : {e}")

if __name__ == "__main__":
    force_fix_ebra()

