import os
import psycopg2
from dotenv import load_dotenv

# Charger .env pour DATABASE_URL
load_dotenv()
DATABASE_URL = os.environ.get("DATABASE_URL")

def check_db_size():
    try:
        url = DATABASE_URL
        if url and "DATABASE_URL=\"" in url:
            url = url.replace("DATABASE_URL=\"", "").replace("\"", "")
        if url and "?pgbouncer=true" in url:
            url = url.replace("?pgbouncer=true", "")
            
        conn = psycopg2.connect(url)
        cur = conn.cursor()
        
        # Taille totale de la base
        cur.execute("SELECT pg_size_pretty(pg_database_size(current_database()))")
        db_size = cur.fetchone()[0]
        
        # Taille de la table Article et de ses index
        cur.execute("""
            SELECT 
                pg_size_pretty(pg_total_relation_size('"Article"')) as total_size,
                pg_size_pretty(pg_relation_size('"Article"')) as table_size,
                pg_size_pretty(pg_total_relation_size('"Article"') - pg_relation_size('"Article"')) as index_size
        """)
        table_stats = cur.fetchone()
        
        # Décompte total
        cur.execute("SELECT COUNT(*) FROM \"Article\"")
        total_count = cur.fetchone()[0]

        print(f"\n--- ÉTAT DE LA BASE DE DONNÉES NEON ---")
        print(f"Nombre total d\'articles : {total_count:,}".replace(',', ' '))
        print(f"Taille totale de la DB  : {db_size}")
        print(f"---------------------------------------")
        print(f"Détail table 'Article' :")
        print(f"  > Total (Data+Index)  : {table_stats[0]}")
        print(f"  > Données seules      : {table_stats[1]}")
        print(f"  > Index seuls         : {table_stats[2]}")

        cur.close()
        conn.close()
    except Exception as e:
        print(f"Erreur : {e}")

if __name__ == "__main__":
    check_db_size()
