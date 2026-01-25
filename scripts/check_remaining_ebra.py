import os
import psycopg2
from dotenv import load_dotenv

load_dotenv(".env.local")
DATABASE_URL = os.environ.get("NEWS_DATABASE_URL")

def check_remaining():
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        
        # Vérification spécifique EBRA
        cur.execute("""
            SELECT COUNT(*) 
            FROM \"Article\" 
            WHERE (source LIKE '%Alsace%' OR source LIKE '%DNA%')
              AND ((\"imageUrl\" IS NULL OR \"imageUrl\" = '') OR (\"description\" IS NULL OR \"description\" = ''))
              AND link NOT LIKE '%google.com%'
        """)
        ebra_count = cur.fetchone()[0]
        
        # Vérification globale (toutes sources)
        cur.execute("""
            SELECT COUNT(*) 
            FROM \"Article\" 
            WHERE ((\"imageUrl\" IS NULL OR \"imageUrl\" = '') OR (\"description\" IS NULL OR \"description\" = ''))
              AND link NOT LIKE '%google.com%'
        """)
        total_count = cur.fetchone()[0]
        
        # Détail par source pour le global
        cur.execute("""
            SELECT source, COUNT(*) as cnt
            FROM \"Article\" 
            WHERE ((\"imageUrl\" IS NULL OR \"imageUrl\" = '') OR (\"description\" IS NULL OR \"description\" = ''))
              AND link NOT LIKE '%google.com%'
            GROUP BY source
            ORDER BY cnt DESC
            LIMIT 10
        """)
        top_sources = cur.fetchall()

        print(f"--- RÉSULTATS ---")
        print(f"Restant EBRA (Alsace/DNA) : {ebra_count}")
        print(f"Total restant (toutes sources) : {total_count}")
        
        if total_count > 0:
            print("\nTop 10 sources avec données manquantes :")
            for source, count in top_sources:
                print(f"- {source}: {count}")

        cur.close()
        conn.close()
    except Exception as e:
        print(f"Erreur : {e}")

if __name__ == "__main__":
    check_remaining()
