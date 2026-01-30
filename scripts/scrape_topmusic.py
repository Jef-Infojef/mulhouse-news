import os
import requests
import psycopg2
import json
from bs4 import BeautifulSoup
from dotenv import load_dotenv
import time
import random

# Configuration
load_dotenv(".env.local")
DATABASE_URL = os.environ.get("DATABASE_URL")

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
}

def get_db_connection():
    clean_url = DATABASE_URL.replace("?pgbouncer=true", "").replace("&pgbouncer=true", "")
    return psycopg2.connect(clean_url)

def fetch_topmusic_content(url):
    try:
        time.sleep(random.uniform(0.5, 1.5))
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code != 200:
            print(f"   ⚠️ Status {response.status_code}")
            return None

        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 1. Extraction via __NEXT_DATA__ (Le Graal sur Top Music)
        next_data_script = soup.find('script', id='__NEXT_DATA__')
        if next_data_script:
            try:
                data = json.loads(next_data_script.string)
                page_data = data['props']['pageProps']['page']
                
                text_parts = []
                
                # Récupération du chapô
                chapo = page_data.get('pageContent', {}).get('chapo', {}).get('content')
                if chapo:
                    text_parts.append(chapo)
                
                # Récupération du corps (stocké dans un JSON stringifié dans blocsData)
                blocs_data_str = page_data.get('pageContent', {}).get('blocsData')
                if blocs_data_str:
                    blocs_data = json.loads(blocs_data_str)
                    corps_html = ""
                    
                    # Le corps peut être dans 'corps' -> 'blocsData'
                    corps_obj = blocs_data.get('corps', {}).get('blocsData', {})
                    for key in corps_obj:
                        block = corps_obj[key]
                        if 'content' in block:
                            corps_html += block['content'] + "\n"
                    
                    if corps_html:
                        # On nettoie le HTML du corps
                        corps_soup = BeautifulSoup(corps_html, 'html.parser')
                        text_parts.append(corps_soup.get_text("\n", strip=True))
                
                if text_parts:
                    return "\n\n".join(text_parts)
            except Exception as e:
                print(f"   ⚠️ Erreur parsing JSON: {e}")

        # 2. Fallback CSS (si jamais le JSON change)
        chapo_tag = soup.find(id='chapo')
        corps_tag = soup.find(class_='CONTENT') # Souvent un conteneur large
        
        text_parts = []
        if chapo_tag:
            text_parts.append(chapo_tag.get_text().strip())
        
        # On cherche les paragraphes dans les sections CONTENT
        for section in soup.find_all('section', class_='CONTENT'):
            for p in section.find_all('p'):
                txt = p.get_text().strip()
                if txt and len(txt) > 10:
                    text_parts.append(txt)
        
        if text_parts:
            return "\n\n".join(text_parts)

        return None

    except Exception as e:
        print(f"   ❌ Erreur fetch: {e}")
        return None

def main():
    print("[*] Démarrage du scraper dédié Top Music...")
    
    conn = get_db_connection()
    cur = conn.cursor()

    # Sélectionner les articles Top Music sans contenu
    cur.execute("""
        SELECT id, title, link 
        FROM \"Article\" 
        WHERE (link LIKE '%topmusic.fr%' OR source LIKE '%Top Music%')
          AND (content IS NULL OR LENGTH(content) < 100)
    """)
    articles = cur.fetchall()
    
    if not articles:
        print("Aucun article Top Music à traiter.")
        return

    print(f"[*] {len(articles)} articles Top Music à traiter.")

    success_count = 0
    for i, (art_id, title, link) in enumerate(articles, 1):
        print(f"[{i}/{len(articles)}] {title[:50]}...")
        
        content = fetch_topmusic_content(link)
        
        if content:
            try:
                cur.execute('UPDATE "Article" SET content = %s WHERE id = %s', (content, art_id))
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
    print(f"\n[*] Terminé. {success_count} articles Top Music mis à jour.")

if __name__ == "__main__":
    main()
