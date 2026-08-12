import os
import requests
import re
import html
import psycopg2
from dotenv import load_dotenv
import time
import random

load_dotenv(".env.local")
DATABASE_URL = os.environ.get("NEWS_DATABASE_URL")

def get_db_connection():
    return psycopg2.connect(DATABASE_URL)

def fetch_content_data(url):
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
    img, desc = None, None
    try:
        time.sleep(random.uniform(0.5, 1.0))
        r = requests.get(url, headers=headers, timeout=10)
        if r.status_code == 200:
            html_c = r.text
            # Image
            m_img = re.search(r'property=["\']og:image["\'][^>]*content=["\']([^"\']+)["\']', html_c)
            if not m_img: m_img = re.search(r'content=["\']([^"\']+)["\'][^>]*property=["\']og:image["\']', html_c)
            if m_img: img = html.unescape(m_img.group(1))
            # Description
            m_desc = re.search(r'property=["\']og:description["\'][^>]*content=["\']([^"\']+)["\']', html_c)
            if not m_desc: m_desc = re.search(r'name=["\']description["\'][^>]*content=["\']([^"\']+)["\']', html_c)
            if m_desc: desc = html.unescape(m_desc.group(1))
    except Exception as e:
        print(f"      [!] Erreur fetch: {e}")
    return img, desc

def main():
    print("[*] Sauvetage des articles L'Est Républicain...")
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT id, title, link, source 
        FROM \"Article\" 
        WHERE (source LIKE '%Est Républicain%')
          AND ((\"imageUrl\" IS NULL OR \"imageUrl\" = '') OR (\"description\" IS NULL OR \"description\" = ''))
          AND link NOT LIKE '%%google.com%%'
        ORDER BY \"publishedAt\" DESC
    """)
    articles = cur.fetchall()
    total = len(articles)
    print(f"[*] {total} articles L'Est Républicain à traiter.")

    repaired = 0
    for i, (art_id, title, link, source) in enumerate(articles, 1):
        print(f"[{i}/{total}] {title[:60]}...")
        img, desc = fetch_content_data(link)
        
        if img or desc:
            updates = []
            params = []
            if img:
                updates.append("\"imageUrl\" = %s")
                params.append(img)
            if desc:
                updates.append("\"description\" = %s")
                params.append(desc)
            
            if updates:
                params.append(art_id)
                query = f"UPDATE \"Article\" SET {', '.join(updates)} WHERE id = %s"
                cur.execute(query, tuple(params))
                conn.commit()
                repaired += 1
                print(f"   ✅ Réparé (Img: {'Oui' if img else 'Non'}, Desc: {'Oui' if desc else 'Non'})")
        else:
            print("   ⚠️ Aucune donnée trouvée")

    cur.close()
    conn.close()
    print(f"\n[*] Terminé. {repaired} articles L'Est Républicain sauvés.")

if __name__ == "__main__":
    main()
