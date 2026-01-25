import os
import psycopg2
from dotenv import load_dotenv

load_dotenv(".env.local")
DATABASE_URL = os.environ.get("NEWS_DATABASE_URL")

RADIO_FRANCE_LOGO = "https://www.radiofrance.fr/static/images/logo_radio_france_full.png"

def force_fix_radio_france():
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        
        # Récupérer les IDs d'abord
        cur.execute("""
            SELECT id FROM "Article" 
            WHERE source LIKE '%Radio France%'
              AND ("imageUrl" IS NULL OR "imageUrl" = '')
              AND ("description" IS NOT NULL AND "description" != '')
        """)
        ids = [row[0] for row in cur.fetchall()]
        
        print(f"[*] {len(ids)} articles à mettre à jour.")
        
        updated = 0
        for art_id in ids:
            cur.execute("UPDATE \"Article\" SET \"imageUrl\" = %s WHERE id = %s", (RADIO_FRANCE_LOGO, art_id))
            updated += 1
        
        conn.commit()
        cur.close()
        conn.close()
        print(f"✅ {updated} articles mis à jour.")

    except Exception as e:
        print(f"Erreur : {e}")

if __name__ == "__main__":
    force_fix_radio_france()
