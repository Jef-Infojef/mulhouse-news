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

# COOKIE ET HEADERS (À mettre à jour si possible)
COOKIE_VAL = "97970E87FF01CC9A9FAC842D8A4644DF~000000000000000000000000000000~YAAQh8RNFyDmeCObAQAA8J5gsR4KnigL2GY9yXsAstD2XqPhezpmTszF46xnseO/QVk6Q7QnPjBxyPTuIE/AHCfC/PiUPIXzlWmIO+RSNeHo5dlPADpLlyv0OIvf4GEJzBLhY3pvodRpC3vEtLrtKN2R7ROSrVosegIfB4dlbRHddn7/2fbCrKz5fYuqjVkCG8ug8PgiqJLZKxdWipKFK1tFbdRP7s67ciFHSeXUd82Wy6NdP/SstAa+37zG9dnbgCmWG2XNT6hJFCwf8HJw4KfvCHozcl0x13oaI3O0WYGyJBQvJbHxZ9qaAfVRXW8kSvaC2nPZhU/JSWmTsKj/uP73Crr7v8bRnL9DxhURUpaqGXaJO99d0daSorJ6e3HqMO9spvH/PYVvpCh/ag=="

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:134.0) Gecko/20100101 Firefox/134.0',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
    'Accept-Language': 'fr,fr-FR;q=0.8,en-US;q=0.5,en;q=0.3',
    'Cookie': f'ak_bmsc={COOKIE_VAL}',
    'Connection': 'keep-alive',
    'Upgrade-Insecure-Requests': '1',
}

def get_db_connection():
    return psycopg2.connect(DATABASE_URL)

def parse_metadata(html_c):
    img, desc = None, None
    # Regex robustes pour Les Echos
    m_img = re.search(r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\\]+)["\\]', html_c)
    if not m_img: m_img = re.search(r'<meta[^>]+content=["\']([^"\\]+)["\\][^>]+property=["\']og:image["\']', html_c)
    
    m_desc = re.search(r'<meta[^>]+property=["\']og:description["\'][^>]+content=["\']([^"\\]+)["\\]', html_c)
    if not m_desc: m_desc = re.search(r'<meta[^>]+content=["\']([^"\\]+)["\\][^>]+property=["\']og:description["\']', html_c)
    if not m_desc: m_desc = re.search(r'<meta[^>]+name=["\']description["\'][^>]+content=["\']([^"\\]+)["\\]', html_c)
    
    if m_img: img = html.unescape(m_img.group(1))
    if m_desc: desc = html.unescape(m_desc.group(1))
    return img, desc

def main():
    print("[*] Lancement du sauvetage massif Les Echos avec session...")
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT id, title, link 
        FROM \"Article\" 
        WHERE source LIKE '%Echos%' 
          AND ((\"imageUrl\" IS NULL OR \"imageUrl\" = '') OR (\"description\" IS NULL OR \"description\" = ''))
          AND link NOT LIKE '%%google.com%%'
        ORDER BY \"publishedAt\" DESC
    """)
    articles = cur.fetchall()
    total = len(articles)
    print(f"[*] {total} articles à traiter.")

    session = requests.Session()
    session.headers.update(headers)

    repaired = 0
    errors_count = 0

    for i, (art_id, title, link) in enumerate(articles, 1):
        try:
            print(f"[{i}/{total}] {title[:50]}...", end=" ", flush=True)
            # Délai très court pour essayer de tout passer avant expiration du cookie
            time.sleep(random.uniform(0.2, 0.5))
            
            r = session.get(link, timeout=15)
            if r.status_code == 200:
                img, desc = parse_metadata(r.text)
                if img or desc:
                    updates = []
                    params = []
                    if img:
                        updates.append("\"imageUrl\" = %s")
                        params.append(img)
                    if desc:
                        updates.append("\"description\" = %s")
                        params.append(desc)
                    
                    params.append(art_id)
                    cur.execute(f"UPDATE \"Article\" SET {', '.join(updates)} WHERE id = %s", tuple(params))
                    conn.commit()
                    repaired += 1
                    print(f"✅")
                else:
                    print(f"⚠️ (Métas non trouvées)")
                errors_count = 0 # Reset des erreurs consécutives
            elif r.status_code == 403:
                print(f"❌ (403 Forbidden - Cookie probablement expiré)")
                errors_count += 1
                if errors_count >= 3:
                    print("!!! Trop d\'erreurs 403 consécutives. Arrêt.")
                    break
            else:
                print(f"❓ (Status {r.status_code})")
        except Exception as e:
            print(f"🔥 Erreur: {e}")
            time.sleep(2)

    cur.close()
    conn.close()
    print(f"\n[*] Terminé. {repaired} articles Les Echos sauvés.")

if __name__ == "__main__":
    main()
