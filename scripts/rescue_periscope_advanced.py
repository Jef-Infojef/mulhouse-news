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

def fetch_content_data_advanced(url):
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
    img, desc = None, None
    try:
        time.sleep(random.uniform(0.5, 1.0))
        r = requests.get(url, headers=headers, timeout=10)
        if r.status_code == 200:
            html_c = r.text
            
            # --- DESCRIPTION ---
            m_desc = re.search(r'property=["\']og:description["\'][^>]*content=["\']([^"\']+)["\']', html_c)
            if not m_desc: m_desc = re.search(r'name=["\']description["\'][^>]*content=["\']([^"\']+)["\']', html_c)
            if m_desc: desc = html.unescape(m_desc.group(1))

            # --- IMAGE (Logique avancée) ---
            # 1. og:image
            m_img = re.search(r'property=["\']og:image["\'][^>]*content=["\']([^"\']+)["\']', html_c)
            if not m_img: m_img = re.search(r'content=["\']([^"\']+)["\'][^>]*property=["\']og:image["\']', html_c)
            
            if m_img: 
                img = html.unescape(m_img.group(1))
            else:
                # 2. Chercher première image de contenu
                # On évite les logos, icônes, et images de navigation
                all_imgs = re.findall(r'<img[^>]+src=["\']([^"\']+)["\']', html_c)
                for candidate in all_imgs:
                    cand = html.unescape(candidate)
                    lower_c = cand.lower()
                    if ("logo" in lower_c or "icon" in lower_c or "facebook" in lower_c or "twitter" in lower_c or "instagram" in lower_c):
                        continue
                    if not (lower_c.endswith(".jpg") or lower_c.endswith(".jpeg") or lower_c.endswith(".png")):
                        continue
                    
                    # On a trouvé un candidat potentiel (ex: .../image-300x200.jpg)
                    img = cand
                    
                    # Tentative de nettoyage de la taille pour avoir la Full HD
                    # Regex pour supprimer -300x200, -150x150 etc à la fin du fichier avant l'extension
                    img_clean = re.sub(r'-\\d+x\\d+(\\.[a-zA-Z]+)$', r'\1', img)
                    
                    # On vérifie si l'image clean existe (HEAD request optionnelle, mais on peut tenter le coup)
                    # Pour faire simple, on prend l'image clean. Si ça casse, on reviendra à la version thumb.
                    img = img_clean 
                    break

    except Exception as e:
        print(f"      [!] Erreur fetch: {e}")
    return img, desc

def main():
    print("[*] Sauvetage AVANCÉ des articles Le Periscope...")
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT id, title, link, source 
        FROM \"Article\" 
        WHERE (source LIKE '%Périscope%' OR link LIKE '%le-periscope.info%')
          AND ((\"imageUrl\" IS NULL OR \"imageUrl\" = '') OR (\"description\" IS NULL OR \"description\" = ''))
          AND link NOT LIKE '%%google.com%%'
        ORDER BY \"publishedAt\" DESC
    """)
    articles = cur.fetchall()
    total = len(articles)
    print(f"[*] {total} articles Le Periscope à traiter.")

    repaired = 0
    for i, (art_id, title, link, source) in enumerate(articles, 1):
        print(f"[{i}/{total}] {title[:60]}...")
        img, desc = fetch_content_data_advanced(link)
        
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
                print(f"   ✅ Réparé (Img: {img[:30]}..., Desc: {'Oui' if desc else 'Non'})")
        else:
            print("   ⚠️ Aucune donnée trouvée")

    cur.close()
    conn.close()
    print(f"\n[*] Terminé. {repaired} articles Le Periscope sauvés.")

if __name__ == "__main__":
    main()
