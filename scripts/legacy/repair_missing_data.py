import os
from curl_cffi import requests
from bs4 import BeautifulSoup
import re
import html
import psycopg2
from dotenv import load_dotenv
import time
import random
from urllib.parse import urljoin

# Charger les variables d'environnement
load_dotenv(".envenv")
load_dotenv(".env.local")
load_dotenv(".env")
DATABASE_URL = os.environ.get("DATABASE_URL")

def get_db_connection():
    if not DATABASE_URL:
        raise ValueError("DATABASE_URL non trouvée")
    # Nettoyage pour psycopg2
    clean_url = DATABASE_URL.replace("?pgbouncer=true", "").replace("&pgbouncer=true", "")
    return psycopg2.connect(clean_url)

def fetch_og_data(url):
    """Tente de récupérer og:image et description avec curl_cffi et BeautifulSoup"""
    if not url or "google.com" in url:
        return None, None
        
    try:
        # On simule un délai humain
        time.sleep(random.uniform(1, 3))
        
        # Tentative avec vérification SSL
        try:
            resp = requests.get(url, impersonate="chrome110", timeout=15, allow_redirects=True)
        except Exception as ssl_err:
            # Si erreur SSL, on retente sans vérification (pour les sites type uha.fr)
            if "CertificateVerifyError" in str(ssl_err) or "SSL" in str(ssl_err):
                resp = requests.get(url, impersonate="chrome110", timeout=15, allow_redirects=True, verify=False)
            else:
                raise ssl_err
        
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, 'html.parser')
            
            # 1. Extraction Image
            img = None
            
            # A. Meta OG Image
            og_image = soup.find("meta", property="og:image")
            if og_image and og_image.get("content"):
                img = html.unescape(og_image["content"])
            
            # B. Fallback Twitter Image
            if not img:
                tw_image = soup.find("meta", attrs={"name": "twitter:image"})
                if tw_image and tw_image.get("content"):
                    img = html.unescape(tw_image["content"])

            # C. Fallback Body Image (Balises <picture>, <figure> ou <img> dans le contenu)
            if not img:
                # Chercher dans picture ou figure (souvent l'image principale)
                pic = soup.find("picture") or soup.find("figure")
                if pic:
                    potential_img = pic.find("img")
                    if potential_img and potential_img.get("src"):
                        img = potential_img["src"]
                
                if not img:
                    # Recherche générique des images .jpg/.png significatives
                    for potential in soup.find_all("img"):
                        src = potential.get("src")
                        if src and any(ext in src.lower() for ext in ['.jpg', '.jpeg', '.png', '.webp', '.avif']):
                            if not any(p in src.lower() for p in ['logo', 'icon', 'ads', 'pub', 'pixel', 'banner']):
                                if 'avatar' not in src.lower():
                                    img = src
                                    break

            # Nettoyage et reconstruction de l'URL de l'image (si relative)
            if img:
                img = html.unescape(img).strip()
                if img.startswith("//"):
                    img = "https:" + img
                elif not img.startswith("http"):
                    img = urljoin(url, img)

            # 2. Extraction Description
            desc = None
            og_desc = soup.find("meta", property="og:description")
            if og_desc and og_desc.get("content"):
                desc = html.unescape(og_desc["content"])
            
            if not desc:
                meta_desc = soup.find("meta", attrs={"name": "description"})
                if meta_desc and meta_desc.get("content"):
                    desc = html.unescape(meta_desc["content"])

            if desc and len(desc) > 250: 
                desc = desc[:247] + "..."
                
            return img, desc
        else:
            print(f"      [!] Erreur HTTP {resp.status_code}")
    except Exception as e:
        print(f"      [!] Exception: {e}")
        
    return None, None

def main():
    print("[*] Démarrage de la réparation des articles sans photo...")
    
    conn = get_db_connection()
    cur = conn.cursor()
    
    # On cible les articles sans photo (limité à 50 pour le test)
    # On exclut les liens google non décodés qui traîneraient
    cur.execute("""
        SELECT id, title, link, source 
        FROM "Article" 
        WHERE ("imageUrl" IS NULL OR "imageUrl" = '') 
          AND link NOT LIKE '%google.com%'
        ORDER BY "publishedAt" DESC
    """)
    articles = cur.fetchall()
    
    print(f"[*] {len(articles)} articles à tenter de réparer.")
    
    success_count = 0
    total_to_repair = len(articles)
    
    for i, (art_id, title, link, source) in enumerate(articles, 1):
        new_img, new_desc = fetch_og_data(link)
        
        if new_img or new_desc:
            try:
                if new_img and new_desc:
                    cur.execute("UPDATE \"Article\" SET \"imageUrl\" = %s, \"description\" = %s WHERE id = %s", (new_img, new_desc, art_id))
                elif new_img:
                    cur.execute("UPDATE \"Article\" SET \"imageUrl\" = %s WHERE id = %s", (new_img, art_id))
                elif new_desc:
                    cur.execute("UPDATE \"Article\" SET \"description\" = %s WHERE id = %s", (new_desc, art_id))
                
                conn.commit()
                success_count += 1
                
                if not new_img:
                    print(f"[{i}/{total_to_repair}] ✅ (Pas d'image) {title[:50]}...")
                    print(f"    URL: {link}")
                else:
                    print(f"[{i}/{total_to_repair}] ✅ {title[:60]}... (Img: OK)")
            except Exception as e:
                conn.rollback()
                print(f"[{i}/{total_to_repair}] ❌ Erreur DB: {e}")
        else:
            print(f"[{i}/{total_to_repair}] ❌ Échec : {title[:50]}...")
            print(f"    URL: {link}")

    print(f"\n[*] Travail terminé. {success_count} articles ont été réparés.")
    cur.close()
    conn.close()

if __name__ == "__main__":
    main()
