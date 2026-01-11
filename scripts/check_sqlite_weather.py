import sqlite3

def list_sqlite_tables():
    try:
        conn = sqlite3.connect('C:/dev/assocommercants/prisma/dev.db')
        cur = conn.cursor()
        cur.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cur.fetchall()
        print("Tables dans SQLite dev.db :")
        for t in tables:
            print(f"- {t[0]}")
            
        # Check weather_history specifically
        cur.execute("SELECT COUNT(*) FROM weather_history;")
        count = cur.fetchone()[0]
        print(f"✅ weather_history trouvée ! Nombre d'entrées : {count}")
        
        cur.close()
        conn.close()
    except Exception as e:
        print(f"❌ Erreur : {e}")

if __name__ == "__main__":
    list_sqlite_tables()
