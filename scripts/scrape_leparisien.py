import os
from curl_cffi import requests
import psycopg2
import json
from bs4 import BeautifulSoup
from dotenv import load_dotenv
import time
import random

# Configuration
load_dotenv(".env.local")
DATABASE_URL = os.environ.get("DATABASE_URL")

def get_db_connection():
    clean_url = DATABASE_URL.replace("?pgbouncer=true", "").replace("&pgbouncer=true", "")
    return psycopg2.connect(clean_url)

def fetch_leparisien_content(url):
    try:
        time.sleep(random.uniform(1.0, 2.0))
        # Utilisation de curl_cffi pour imiter un vrai navigateur
        response = requests.get(url, impersonate="chrome120", timeout=15)
        
        if response.status_code != 200:
            print(f"   ⚠️ Status {response.status_code}")
            return None

        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 1. Tentative via JSON-LD
        scripts = soup.find_all('script', type='application/ld+json')
        for script in scripts:
            try:
                # Le Parisien met parfois plusieurs objets dans un tableau []
                content_json = script.string.strip()
                data_list = json.loads(content_json)
                if not isinstance(data_list, list):
                    data_list = [data_list]
                
                for data in data_list:
                    if isinstance(data, dict) and data.get('@type') == 'NewsArticle' and 'articleBody' in data:
                        return data['articleBody']
            except:
                continue

        # 2. Fallback CSS
        text_parts = []
        
        # Chapô
        subheadline = soup.find('p', class_='subheadline')
        if subheadline:
            text_parts.append(subheadline.get_text().strip())
            
        # Corps
        content_sections = soup.select('.article-section .content')
        for section in content_sections:
            # On ignore les blocs "A lire aussi" ou pubs insérés
            if section.find(class_='article-read-also_container') or section.find(class_='ad_element'):
                continue
                
            for element in section.find_all(['p', 'h2']):
                # On évite les paragraphes de signature ou trop courts
                txt = element.get_text().strip()
                if txt and len(txt) > 20:
                    text_parts.append(txt)

        if text_parts:
            # Unicité
            unique = []
            for p in text_parts:
                if p not in unique:
                    unique.append(p)
            return "\n\n".join(unique)

        return None

    except Exception as e:
        print(f"   ❌ Erreur fetch: {e}")
        return None

def main():
    print("[*] Démarrage du scraper dédié Le Parisien...")
    
    conn = get_db_connection()
    cur = conn.cursor()

    # Sélectionner les articles Le Parisien sans contenu
    cur.execute("""
        SELECT id, title, link 
        FROM \"Article\" 
        WHERE (link LIKE '%leparisien.fr%' OR source LIKE '%Le Parisien%')
          AND (content IS NULL OR LENGTH(content) < 100)
    """)
    articles = cur.fetchall()
    
    if not articles:
        print("Aucun article Le Parisien à traiter.")
        return

    print(f"[*] {len(articles)} articles Le Parisien à traiter.")

    success_count = 0
    for i, (art_id, title, link) in enumerate(articles, 1):
        print(f"[{i}/{len(articles)}] {title[:50]}...")
        
        content = fetch_leparisien_content(link)
        
        if content:
            try:
                cur.execute('UPDATE \"Article\" SET content = %s WHERE id = %s', (content, art_id))
                conn.commit()
                print(f"   ✅ Contenu récupéré ({len(content)} chars)")
                success_count += 1
            except Exception as e:
                print(f"   ❌ Erreur BDD: {e}")
                conn.rollback()
        else:
            print("   ⚠️ Contenu non trouvé")

    cur.close()
    conn.close()
    print(f"\n[*] Terminé. {success_count} articles Le Parisien mis à jour.")

if __name__ == "__main__":
    main()
