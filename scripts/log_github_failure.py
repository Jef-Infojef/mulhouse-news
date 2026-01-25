import os
import psycopg2
from datetime import datetime

def log_failure():
    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        return

    try:
        clean_url = db_url.replace("?pgbouncer=true", "").replace("&pgbouncer=true", "")
        conn = psycopg2.connect(clean_url)
        cur = conn.cursor()
        
        cur.execute("""
            INSERT INTO "ScrapingLog" (id, "startedAt", "finishedAt", status, "errorMessage")
            VALUES (gen_random_uuid(), NOW(), NOW(), 'GITHUB_CRASH', %s)
        """, ('GitHub Action a échoué avant ou pendant l\'exécution du script principal.',))
        conn.commit()
        cur.close()
        conn.close()
        print("✅ Log d\'échec critique enregistré en base.")
    except Exception as e:
        print(f"❌ Impossible d\'enregistrer le log d\'échec : {e}")

if __name__ == "__main__":
    log_failure()

