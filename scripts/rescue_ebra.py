import os
import requests
import re
import html
import psycopg2
from dotenv import load_dotenv
import time
import random

# Configuration
load_dotenv(".env.local")
DATABASE_URL = "postgresql://postgres.wmvjpdedrfyttixdkzpi:05v0Ije8JayPNsaI@aws-1-eu-west-3.pooler.supabase.com:5432/postgres"

def get_db_connection():
    return psycopg2.connect(DATABASE_URL)

def fetch_content_data(url):
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
    img, desc = None, None
    try:
        time.sleep(random.uniform(0.3, 0.6))
        r = requests.get(url, headers=headers, timeout=10, allow_redirects=True)
        if r.status_code == 200:
            html_c = r.text
            # Image
            m_img = re.search(r'property=["\']og:image["\'][^>]*content=["\']([^"\\]+)["\\]', html_c)
            if not m_img: m_img = re.search(r'content=["\']([^"\\]+)["\\][^>]*property=["\']og:image["\\]', html_c)
            if m_img: img = html.unescape(m_img.group(1))
            # Description
            m_desc = re.search(r'property=["\']og:description["\'][^>]*content=["\']([^"\\]+)["\\]', html_c)
            if not m_desc: m_desc = re.search(r'name=["\']description["\'][^>]*content=["\']([^"\\]+)["\\]', html_c)
            if m_desc: desc = html.unescape(m_desc.group(1))
    except: pass
    return img, desc

def main():
    print("[*] Reprise du sauvetage Alsace/DNA...")
    
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT id, title, link, source 
        FROM \"Article\" 
        WHERE (source LIKE '%Alsace%' OR source LIKE '%DNA%')
          AND ((\"imageUrl\" IS NULL OR \"imageUrl\" = '') OR (\"description\" IS NULL OR \"description\" = ''))
          AND link NOT LIKE '%%google.com%%'
        ORDER BY \"publishedAt\" DESC
    """)
    articles = cur.fetchall()
    total = len(articles)
    print(f"[*] {total} articles restants à traiter.")

    repaired = 0
    for i, (art_id, title, link, source) in enumerate(articles, 1):
        try:
            # Vérifier si la connexion est toujours vivante
            if conn.closed:
                print("🔄 Reconnexion à la base de données...")
                conn = get_db_connection()
                cur = conn.cursor()

            print(f"[{i}/{total}] {source} | {title[:50]}...")
            img, desc = fetch_content_data(link)
            
            if img or desc:
                if img and desc:
                    cur.execute("UPDATE \"Article\" SET \"imageUrl\" = %s, \"description\" = %s WHERE id = %s", (img, desc, art_id))
                elif img:
                    cur.execute("UPDATE \"Article\" SET \"imageUrl\" = %s WHERE id = %s", (img, art_id))
                elif desc:
                    cur.execute("UPDATE \"Article\" SET \"description\" = %s WHERE id = %s", (desc, art_id))
                conn.commit()
                repaired += 1
                print(f"   ✅ OK")
            else:
                print("   ⚠️ Vide")
        except Exception as e:
            print(f"   ❌ Erreur sur cet article: {e}")
            try: conn.rollback()
            except: pass
            time.sleep(2) # Petite pause en cas d'erreur réseau

    cur.close()
    conn.close()
    print(f"\n[*] Terminé. {repaired} articles supplémentaires sauvés.")

if __name__ == "__main__":
    main()