import psycopg2
from psycopg2.extras import execute_values
import os
from dotenv import load_dotenv

load_dotenv(".env.local")

# Source: Neon (assocommercants)
NEON_URL = "postgresql://neondb_owner:npg_GX8cJA3bwtQO@ep-cool-mouse-agtxokbb-pooler.c-2.eu-central-1.aws.neon.tech/neondb?sslmode=require"

# Destination: Supabase (mulhouse-news)
SUPABASE_URL = "postgresql://postgres.wmvjpdedrfyttixdkzpi:05v0Ije8JayPNsaI@aws-1-eu-west-3.pooler.supabase.com:5432/postgres"

def migrate_weather():
    try:
        # Connexion Source
        print("[*] Connexion à Neon (Source)...")
        conn_src = psycopg2.connect(NEON_URL)
        cur_src = conn_src.cursor()
        
        # Connexion Destination
        print("[*] Connexion à Supabase (Destination)...")
        conn_dst = psycopg2.connect(SUPABASE_URL)
        cur_dst = conn_dst.cursor()
        
        # Récupération des données
        print("[*] Lecture des données météo historiques...")
        cur_src.execute('SELECT location, day, month, year, "tempMax", "tempMin", "weatherCode", "createdAt" FROM weather_history;')
        all_rows = cur_src.fetchall()
        total = len(all_rows)
        print(f"[+] {total} lignes à transférer.")
        
        # Insertion par paquets
        batch_size = 1000
        count = 0
        
        query = """
        INSERT INTO "WeatherHistory" (id, location, day, month, year, "tempMax", "tempMin", "weatherCode", "createdAt")
        VALUES %s
        ON CONFLICT (location, day, month, year) DO NOTHING;
        """
        
        # Générer des IDs uniques (cuid-like ou simplement un compteur + préfixe)
        import uuid
        
        for i in range(0, total, batch_size):
            batch = all_rows[i:i + batch_size]
            # Préparation des données avec un ID généré
            data_to_insert = []
            for row in batch:
                data_to_insert.append((str(uuid.uuid4()), *row))
            
            execute_values(cur_dst, query, data_to_insert)
            conn_dst.commit()
            count += len(batch)
            print(f"   Transféré : {count}/{total}...")
            
        print("\n✅ Migration terminée avec succès !")
        
        cur_src.close()
        conn_src.close()
        cur_dst.close()
        conn_dst.close()
        
    except Exception as e:
        print(f"\n❌ Erreur lors de la migration : {e}")

if __name__ == "__main__":
    migrate_weather()
