import psycopg2
import os
from dotenv import load_dotenv

# Utilisation de l'URL du pooler qui fonctionne
url = "postgresql://postgres.wmvjpdedrfyttixdkzpi:05v0Ije8JayPNsaI@aws-1-eu-west-3.pooler.supabase.com:5432/postgres"

def find_weather_history():
    try:
        conn = psycopg2.connect(url)
        cur = conn.cursor()
        
        print("[*] Recherche de la table weather_history dans TOUS les schémas...")
        query = """
        SELECT table_schema, table_name 
        FROM information_schema.tables 
        WHERE table_name = 'weather_history';
        """
        cur.execute(query)
        results = cur.fetchall()
        
        if results:
            for schema, name in results:
                print(f"✅ Trouvée : {schema}.{name}")
                # Compter les entrées
                cur.execute(f'SELECT COUNT(*) FROM "{schema}"."{name}"')
                count = cur.fetchone()[0]
                print(f"   Nombre d'entrées : {count}")
        else:
            print("❌ Table non trouvée dans information_schema.")
            
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Erreur : {e}")

if __name__ == "__main__":
    find_weather_history()
