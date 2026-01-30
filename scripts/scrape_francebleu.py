import os
import requests
import psycopg2
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

def fetch_francebleu_content(url):
    try:
        time.sleep(random.uniform(0.5, 1.5))
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code != 200:
            print(f"   ⚠️ Status {response.status_code}")
            return None

        soup = BeautifulSoup(response.text, 'html.parser')
        
        text_parts = []

        # 1. Le Chapô (standfirst)
        standfirst = soup.find('p', class_='standfirst')
        if standfirst:
            text_parts.append(standfirst.get_text().strip())

        # 2. Le corps (IciBody)
        body_div = soup.find('div', class_='IciBody')
        if body_div:
            # On récupère tous les paragraphes directs du corps
            # Note: France Bleu utilise parfois des structures de paragraphes très imbriquées avec Svelte
            paragraphs = body_div.find_all('p')
            for p in paragraphs:
                txt = p.get_text().strip()
                # On évite les paragraphes vides ou les pubs (souvent dans des div svelte-xxx)
                if txt and len(txt) > 5:
                    # On vérifie si c'est pas un texte de pub générique
                    if "Passer la publicité" not in txt and "Revenir avant la publicité" not in txt:
                        text_parts.append(txt)

        if text_parts:
            return "\n\n".join(text_parts)
        
        return None

    except Exception as e:
        print(f"   ❌ Erreur fetch: {e}")
        return None

def main():
    print("[*] Démarrage du scraper dédié France Bleu / ICI...")
    
    conn = get_db_connection()
    cur = conn.cursor()

    # Sélectionner les articles France Bleu sans contenu (ou avec seulement le lien dans content)
    cur.execute("""
        SELECT id, title, link 
        FROM \"Article\" 
        WHERE link LIKE '%francebleu.fr%' 
          AND (content IS NULL OR LENGTH(content) < 100)
    """)
    articles = cur.fetchall()
    
    if not articles:
        print("Aucun article France Bleu à traiter.")
        return

    print(f"[*] {len(articles)} articles France Bleu à traiter.")

    success_count = 0
    for i, (art_id, title, link) in enumerate(articles, 1):
        print(f"[{i}/{len(articles)}] {title[:50]}...")
        
        content = fetch_francebleu_content(link)
        
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
    print(f"\n[*] Terminé. {success_count} articles France Bleu mis à jour.")

if __name__ == "__main__":
    main()
