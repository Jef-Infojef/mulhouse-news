import os
import psycopg2
from dotenv import load_dotenv

# Configuration
def load_env():
    root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    env_files = [".envenv", ".env.local", ".env"]
    for f in env_files:
        path = os.path.join(root_dir, f)
        if os.path.exists(path):
            load_dotenv(path)
            if os.environ.get("DATABASE_URL"):
                break
    load_dotenv()

load_env()
DATABASE_URL = os.environ.get("DATABASE_URL")

def get_db_connection():
    url = DATABASE_URL
    if url and "DATABASE_URL=\"" in url:
        url = url.replace("DATABASE_URL=\"", "").replace("\"", "")
    if url and "?pgbouncer=true" in url:
        url = url.replace("?pgbouncer=true", "")
    return psycopg2.connect(url)

def main():
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        query = """
            SELECT 
                EXTRACT(YEAR FROM "publishedAt") as year,
                COUNT(*) as total,
                SUM(CASE WHEN content IS NOT NULL AND length(content) > 100 THEN 1 ELSE 0 END) as with_content,
                SUM(CASE WHEN "imageUrl" IS NOT NULL AND "imageUrl" <> '' THEN 1 ELSE 0 END) as with_image
            FROM "Article"
            WHERE "publishedAt" >= '2021-01-01' AND "publishedAt" <= '2026-12-31'
              AND (source ILIKE '%Alsace%' OR link LIKE '%lalsace.fr%')
            GROUP BY year
            ORDER BY year DESC;
        """
        
        cur.execute(query)
        rows = cur.fetchall()
        
        print("\n" + "="*65)
        print(f"{ 'RAPPORT L''ALSACE : 2021 - 2026':^65}")
        print("="*65)
        print(f"{ 'Année':<8} | {'Total':<10} | {'Contenu':<10} | {'Photos':<10} | {'% Compl.'}")
        print("-" * 65)
        
        g_total = 0
        g_content = 0
        g_image = 0
        
        for row in rows:
            year = int(row[0])
            total = int(row[1])
            content = int(row[2])
            image = int(row[3])
            
            g_total += total
            g_content += content
            g_image += image
            
            pct = (content / total * 100) if total > 0 else 0
            
            print(f"{year:<8} | {total:<10} | {content:<10} | {image:<10} | {pct:>7.1f}%")
            
        print("-" * 65)
        g_pct = (g_content / g_total * 100) if g_total > 0 else 0
        print(f"{ 'TOTAL':<8} | {g_total:<10} | {g_content:<10} | {g_image:<10} | {g_pct:>7.1f}%")
        print("="*65)

        cur.close()
        conn.close()
    except Exception as e:
        print(f"Erreur : {e}")

if __name__ == "__main__":
    main()
