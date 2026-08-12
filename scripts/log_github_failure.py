import os
import psycopg2
from datetime import datetime

import convex_client

def log_failure():
    # Backend : Convex si CONVEX_DEPLOY_KEY définie, sinon Supabase.
    if convex_client.use_convex():
        try:
            convex_client.insert_scraping_log(
                started_at=datetime.now(),
                finished_at=datetime.now(),
                status="GITHUB_CRASH",
                error_message=(
                    "GitHub Action a échoué avant ou pendant l'exécution du script principal."
                ),
            )
            print("✅ Log d'échec critique enregistré (Convex).")
        except Exception as e:
            print(f"❌ Impossible d'enregistrer le log d'échec : {e}")
        return

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
        print("✅ Log d'échec critique enregistré en base.")
    except Exception as e:
        print(f"❌ Impossible d'enregistrer le log d'échec : {e}")

if __name__ == "__main__":
    log_failure()
