import os
import psycopg2
from dotenv import load_dotenv

load_dotenv(".env.local")
DATABASE_URL = os.environ.get("NEWS_DATABASE_URL")

def check_db_size():
    try:
        conn = psycopg2.connect(DATABASE_URL)
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
        
        print(f"--- TAILLE DE LA BASE DE DONNÉES ---")
        print(f"Taille Totale (DB) : {db_size}")
        print(f"------------------------------------")
        print(f"Table 'Article' (Total) : {table_stats[0]}")
        print(f"  > Données brutes      : {table_stats[1]}")
        print(f"  > Index               : {table_stats[2]}")

        cur.close()
        conn.close()
    except Exception as e:
        print(f"Erreur : {e}")

if __name__ == "__main__":
    check_db_size()
