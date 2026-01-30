import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()
DATABASE_URL = os.environ.get("DATABASE_URL")

def count_articles_by_year():
    try:
        # Nettoyage de l'URL pour psycopg2 si nécessaire
        url = DATABASE_URL
        if url and "DATABASE_URL=\"" in url:
            url = url.replace("DATABASE_URL=\"", "").replace("\"", "")
        
        conn = psycopg2.connect(url)
        cur = conn.cursor()
        
        query = """
            SELECT 
                EXTRACT(YEAR FROM "publishedAt") as year,
                COUNT(*) as total
            FROM "Article"
            WHERE "publishedAt" < '2021-01-01'
              AND (source ILIKE '%Alsace%' OR link LIKE '%lalsace.fr%')
            GROUP BY year
            ORDER BY year DESC;
        """
        
        cur.execute(query)
        rows = cur.fetchall()
        
        print("\n--- Décompte des articles avant 2021 ---")
        print(f"{ 'Année':<10} | { 'Quantité':<10}")
        print("-" * 25)
        
        grand_total = 0
        for row in rows:
            year = int(row[0])
            count = row[1]
            grand_total += count
            print(f"{year:<10} | {count:<10}")
            
        print("-" * 25)
        print(f"{ 'TOTAL':<10} | {grand_total:<10}")

        cur.close()
        conn.close()
    except Exception as e:
        print(f"Erreur : {e}")

if __name__ == "__main__":
    count_articles_by_year()
