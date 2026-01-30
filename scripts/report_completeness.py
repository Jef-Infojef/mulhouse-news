import os
import psycopg2
from dotenv import load_dotenv

load_dotenv(".env.local")
DATABASE_URL = os.environ.get("NEWS_DATABASE_URL")

def report_completeness():
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        
        # Stats globales
        cur.execute("SELECT COUNT(*) FROM \"Article\"")
        total = cur.fetchone()[0]
        
        cur.execute("SELECT COUNT(*) FROM \"Article\" WHERE \"imageUrl\" IS NOT NULL AND \"imageUrl\" != ''")
        with_image = cur.fetchone()[0]
        
        cur.execute("SELECT COUNT(*) FROM \"Article\" WHERE \"description\" IS NOT NULL AND \"description\" != ''")
        with_desc = cur.fetchone()[0]
        
        cur.execute("SELECT COUNT(*) FROM \"Article\" WHERE (\"imageUrl\" IS NOT NULL AND \"imageUrl\" != '') AND (\"description\" IS NOT NULL AND \"description\" != '')")
        complete = cur.fetchone()[0]
        
        # Stats manquantes
        cur.execute("SELECT COUNT(*) FROM \"Article\" WHERE (\"imageUrl\" IS NULL OR \"imageUrl\" = '')")
        missing_image = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM \"Article\" WHERE (\"description\" IS NULL OR \"description\" = '')")
        missing_desc = cur.fetchone()[0]

        print(f"--- RAPPORT DE COMPLÉTUDE ---")
        print(f"Total articles          : {total}")
        print(f"-----------------------------")
        print(f"✅ Articles complets    : {complete} ({complete/total*100:.1f}%)")
        print(f"-----------------------------")
        print(f"🖼️ Avec Image           : {with_image} ({with_image/total*100:.1f}%)")
        print(f"❌ Sans Image           : {missing_image} ({missing_image/total*100:.1f}%)")
        print(f"-----------------------------")
        print(f"📝 Avec Description     : {with_desc} ({with_desc/total*100:.1f}%)")
        print(f"❌ Sans Description     : {missing_desc} ({missing_desc/total*100:.1f}%)")

        cur.close()
        conn.close()
    except Exception as e:
        print(f"Erreur : {e}")

if __name__ == "__main__":
    report_completeness()
