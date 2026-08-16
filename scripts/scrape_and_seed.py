import sys
print(f"DEBUG: Starting script with Python {sys.version}")
import os
import json
from curl_cffi import requests
from bs4 import BeautifulSoup
import xml.etree.ElementTree as ET
import re
import html
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from googlenewsdecoder import gnewsdecoder
import psycopg2
from psycopg2 import sql
from dotenv import load_dotenv
import time
import random
from urllib.parse import urljoin
import unicodedata
from scrape_utils import extract_image_caption
import convex_client

# Charger les variables d'environnement
load_dotenv()

# Configuration
DATABASE_URL = os.environ.get("DATABASE_URL")
if not DATABASE_URL:
    print("DEBUG: DATABASE_URL is missing!")
else:
    print(f"DEBUG: DATABASE_URL found (length: {len(DATABASE_URL)})")

# Backend : Convex (cloud) si USE_CONVEX=1 ou CONVEX_DEPLOY_KEY définie,
# sinon Supabase (psycopg2) comme avant la Phase 3.
USE_CONVEX = convex_client.use_convex()
if USE_CONVEX:
    print("[*] Backend: Convex (cloud)")
else:
    print("[*] Backend: Supabase (psycopg2)")

def build_google_news_url(query: str) -> str:
    """Construit une URL RSS Google News standardisée."""
    return f"https://news.google.com/rss/search?q={query}&hl=fr&gl=FR&ceid=FR:fr"

FEEDS = [
    {"name": "L'Alsace", "url": "https://www.lalsace.fr/rss", "is_google": False},
    {"name": "DNA", "url": "https://www.dna.fr/rss", "is_google": False},
    {"name": "Google News", "url": build_google_news_url("Mulhouse"), "is_google": True}
]
MAX_CONSECUTIVE_DECODE_ERRORS = 3

def get_db_connection():
    if not DATABASE_URL:
        raise Exception("DATABASE_URL non définie")
    clean_url = DATABASE_URL.replace("?pgbouncer=true", "").replace("&pgbouncer=true", "")
    return psycopg2.connect(clean_url)

def extract_real_url(google_url):
    try:
        decoded = gnewsdecoder(google_url)
        if decoded.get("status"):
            return decoded["decoded_url"]
        else:
            print(f"    [!] Échec décodage Google: {decoded.get('message', 'Erreur inconnue')}")
    except Exception as e:
        print(f"    [!] Exception décodage: {e}")
    return google_url

def fetch_content_data(url, fetch_title=False):
    img, desc, title, caption = None, None, None, None
    try:
        time.sleep(random.uniform(0.5, 1.5))
        
        # Tentative avec impersonation chrome pour contourner les protections
        try:
            resp = requests.get(url, timeout=20, allow_redirects=True, impersonate="chrome110")
        except Exception:
            # Fallback sans vérification SSL pour les sites avec certificats mal configurés
            resp = requests.get(url, timeout=20, allow_redirects=True, impersonate="chrome110", verify=False)

        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, 'html.parser')
            
            # 1. Extraction Titre (si demandé ou si titre RSS corrompu)
            if fetch_title:
                og_title = soup.find("meta", property="og:title")
                if og_title and og_title.get("content"):
                    title = html.unescape(og_title["content"])
                else:
                    h1 = soup.find("h1")
                    if h1:
                        title = h1.get_text().strip()

            # 2. Extraction Image
            og_image = soup.find("meta", property="og:image")
            if og_image and og_image.get("content"):
                candidate = html.unescape(og_image["content"])
                # FIX: Ignorer les logos Yahoo génériques et les placeholders de protection (Radware, etc.)
                candidate_lower = candidate.lower()
                if "yahoo" in url.lower() and ("yahoo_frontpage" in candidate_lower or "yahoo-logo" in candidate_lower):
                    img = None 
                elif any(p in candidate_lower for p in ["image.png", "placeholder", "radware", "default-og", "facebook-share", "fb-logo", "generic-article"]):
                    img = None
                else:
                    img = candidate
            
            # Fallback Twitter Image
            if not img:
                tw_image = soup.find("meta", attrs={"name": "twitter:image"})
                if tw_image and tw_image.get("content"):
                    img = html.unescape(tw_image["content"])

            # Fallback Body Image
            if not img:
                # On cherche d'abord dans les classes spécifiques aux articles (ex: caas-img pour Yahoo)
                caas_img = soup.find("img", class_="caas-img")
                if caas_img and caas_img.get("src"):
                    img = caas_img["src"]
                
                if not img:
                    for potential in soup.find_all("img"):
                        src = potential.get("src")
                        if src and any(ext in src.lower() for ext in ['.jpg', '.jpeg', '.png', '.webp', '.avif']):
                            # Filtres plus stricts pour les logos
                            if not any(p in src.lower() for p in ['logo', 'icon', 'ads', 'pub', 'pixel', 'banner', 'loader']):
                                img = src
                                break

            # Nettoyage URL image
            if img:
                img = html.unescape(img).strip()
                if img.startswith("//"):
                    img = "https:" + img
                elif not img.startswith("http"):
                    img = urljoin(url, img)

            # 3. Légende photo
            caption = extract_image_caption(soup, url)

            # 4. Extraction Description
            og_desc = soup.find("meta", property="og:description")
            if og_desc and og_desc.get("content"):
                candidate_desc = html.unescape(og_desc["content"])
                if "loader page" in candidate_desc.lower() or "javascript" in candidate_desc.lower():
                    desc = None
                else:
                    desc = candidate_desc
            else:
                meta_desc = soup.find("meta", attrs={"name": "description"})
                if meta_desc and meta_desc.get("content"):
                    desc = html.unescape(meta_desc["content"])
    except Exception:
        pass
    
    # Sécurité finale : si le titre récupéré est un message de blocage, on l'annule
    if title and ("radware" in title.lower() or "bot" in title.lower() or "page de chargement" in title.lower()):
        title = None

    return img, desc, title, caption

def load_tags(cur):
    """Charge tous les tags depuis le backend et retourne [(id, name, slug, keywords)].
    Convex : id = supabaseId (cuid) des newsTags ; Supabase : id de la table NewsTag."""
    if USE_CONVEX:
        rows = convex_client.get_news_tags()
        db_rows = [(t["id"], t["name"], t["slug"]) for t in rows]
    else:
        cur.execute('SELECT id, name, slug FROM "NewsTag"')
        db_rows = cur.fetchall()
    
    # Mapping tag slug -> mots-clés pour la détection automatique
    TAG_KEYWORDS = {
        'municipales-2026': [
            'municipales', 'municipales 2026', 'élections municipales',
            'conseil municipal', 'restaurer mulhouse', 'lutte ouvrière',
            'taffarelli', 'michèle lutz',
        ],
        'sports': [
            'sport', 'sportif', 'football', 'rugby', 'basket', 'basket-ball', 'basketball', 'handball',
            'volley-ball', 'volleyball', 'natation', 'tennis', 'cyclisme', 'athlétisme',
            'hockey', 'badminton', 'boxe', 'judo', 'karaté', 'escrime', 'aviron',
            'panthères mulhouse', 'mustangs mulhouse', 'fc mulhouse', 'ash mulhouse', 'mhsc', 'mulhouse volley', 'mulhouse foot',
            'championnat', 'play-off', 'play-offs', 'national 2', 'nationale 2', 'national 3', 'nationale 3', 'régional 1', 'régional 2',
            'top 12', 'coupe cev', 'ligue des champions', 'europa league',
            'pro a', 'pro b', 'nm1', 'nm2',
        ],
        'sorties': [
            'sortie', 'exposition', 'concert', 'spectacle', 'festival', 'théâtre', 'cinéma',
            'musée', 'agenda', 'événement', 'soirée', 'fête', 'carnaval',
            'animation', 'culture', 'culturel', 'vernissage', 'conférence', 'atelier',
            'librairie', 'livre', 'lecture', 'visite', 'balade', 'randonnée',
            'zoo', 'parc', 'piscine', 'patinoire', 'curling', 'nuit du', 'noumatrouff',
            'portes ouvertes', 'porte ouverte', 'portes o', 'porte-o',
        ],
        'economie': [
            'économie', 'entreprise', 'emploi', 'chômage', 'investissement', 'budget',
            'finances', 'bilan', 'croissance', 'industrie', 'usine',
            'startup', 'innovation', 'technologie', 'psa',
            'stellantis', 'aéroport', 'bâtiment', 'construction', 'logement',
            'immobilier', 'loyer', 'fiscalité', 'taxe', 'subvention',
        ],
        'commerce': [
            'commerce', 'magasin', 'boutique', 'enseigne', 'centre commercial',
            'galerie marchande', 'boulangerie', 'restaurant', 'café',
            'braderie', 'vente', 'soldes', 'promotion',
            'franchise', 'grande surface', 'supermarché',
        ],
    }
    
    tags = []
    for tag_id, name, slug in db_rows:
        keywords = TAG_KEYWORDS.get(slug, [name.lower()])
        tags.append({'id': tag_id, 'name': name, 'slug': slug, 'keywords': keywords})
    
    return tags


def normalize_text(text):
    """Normalise le texte en minuscules et supprime les accents."""
    if not text:
        return ''
    text = text.lower()
    text = ''.join(c for c in unicodedata.normalize('NFKD', text) if not unicodedata.combining(c))
    return text

def detect_tags(title, description, tags):
    """Retourne la liste des tag IDs correspondant au contenu de l'article."""
    haystack = normalize_text(f"{title} {description or ''}")
    matched = []

    for tag in tags:
        for kw in tag['keywords']:
            if normalize_text(kw) in haystack:
                matched.append(tag['id'])
                break

    return matched


def assign_tags_to_article(cur, article_id, tag_ids):
    """Insère les liens article <-> tag dans ArticleGoogleTag.
    article_id est l'UUID Supabase d'origine (supabaseId côté Convex)."""
    if USE_CONVEX:
        rows = [{"articleId": article_id, "tagId": tag_id} for tag_id in tag_ids]
        if rows:
            convex_client.upsert_article_google_tags(rows)
        return
    for tag_id in tag_ids:
        try:
            cur.execute("""
                INSERT INTO "ArticleGoogleTag" ("articleId", "tagId")
                VALUES (%s, %s)
                ON CONFLICT DO NOTHING
            """, (article_id, tag_id))
        except Exception as e:
            print(f"      [!] Erreur assignation tag: {e}")


def main():
    print(f"[*] Démarrage Mulhouse Actu Multi-Scraper - {datetime.now().strftime('%H:%M:%S')}")
    
    conn = None
    cur = None
    if not USE_CONVEX:
        try:
            conn = get_db_connection()
            cur = conn.cursor()
        except Exception as e:
            print(f"[!] Erreur DB: {e}")
            return
    
    # Chargement des tags depuis le backend
    tags = load_tags(cur)
    print(f"[*] {len(tags)} tags chargés: {[t['name'] for t in tags]}")

    new_count = 0
    titles_seen_this_run = set()
    
    # Statistiques pour le log
    stats = {
        "total_rss_items": 0,
        "duplicates_title": 0,
        "duplicates_link": 0,
        "google_decode_errors": 0,
        "inserted_articles": []
    }
    start_time = datetime.now()

    for feed in FEEDS:
        print(f"\n--- Scraping Flux: {feed['name']} ---")
        try:
            resp = requests.get(feed['url'], timeout=15, impersonate="chrome110")
            print(f"DEBUG: Feed {feed['name']} status: {resp.status_code}")
            
            # Nettoyage rapide du XML pour éviter les erreurs de tokens invalides
            xml_content = resp.content.decode('utf-8', errors='ignore')
            # Remplacement des entités courantes qui font planter le parseur XML
            xml_content = xml_content.replace('&nbsp;', ' ')
            
            soup_rss = BeautifulSoup(xml_content, 'xml')
            items = soup_rss.find_all("item")
        except Exception as e:
            print(f"[!] Erreur sur le flux {feed['name']}: {e}")
            continue

        print(f"[+] {len(items)} articles trouvés.")
        stats["total_rss_items"] += len(items)
        consecutive_decode_errors = 0
        
        for item in items[:100]:
            title_tag = item.find("title")
            raw_title = title_tag.text if title_tag else "Sans titre"
            # Nettoyage profond du titre (enlève les \n, \r, \t et espaces multiples)
            title = " ".join(raw_title.split()).strip()
            
            # Normalisation du titre pour la déduplication (enlève " - Source")
            normalized_title = re.sub(r' - [a-zA-Z0-9\.]+$', '', title).strip()
            
            # Filtre de sécurité
            if "$" in title: continue

            desc_tag = item.find("description")
            raw_desc = desc_tag.text if desc_tag else ""
            desc_text = " ".join(raw_desc.split()).lower()

            # Normalisation Unicode pour les comparaisons (enlève les accents et caractères spéciaux)
            clean_title = normalize_text(title)
            clean_desc = normalize_text(desc_text)
            
            is_mulhouse = "mulhous" in clean_title or "mulhous" in clean_desc
            
            if not feed['is_google'] and not is_mulhouse:
                continue

            if normalized_title in titles_seen_this_run:
                continue
            
            link_tag = item.find("link")
            raw_link = link_tag.text.strip() if link_tag else ""
            
            pub_date_tag = item.find("pubDate") or item.find("pubdate")
            pub_date_str = pub_date_tag.text.strip() if pub_date_tag else ""
            
            if feed['is_google']:
                source_tag = item.find("source")
                source = source_tag.text if source_tag else "Inconnu"
            else:
                source = feed['name']

            if not raw_link: continue

            # 1. Dédup titre (SQL uniquement). Convex : by_link plus bas,
            # un document, pas un scan de 500 articles complets par item RSS.
            if not USE_CONVEX:
                cur.execute("SELECT id FROM \"Article\" WHERE title = %s AND \"publishedAt\" > NOW() - INTERVAL '48 hours'", (title,))
                if cur.fetchone():
                    titles_seen_this_run.add(normalized_title)
                    stats["duplicates_title"] += 1
                    continue

            # 2. Décodage (uniquement pour Google)
            if feed['is_google']:
                real_url = extract_real_url(raw_link)
                # Si le décodage échoue, on saute l'article pour ne pas polluer la DB avec des liens inexploitables
                if "google.com" in real_url:
                    print(f"    [!] Saut : Échec décodage Google pour {title[:40]}...")
                    stats["google_decode_errors"] += 1
                    continue
            else:
                real_url = raw_link

            # 3. Vérifier doublon final (Lien)
            if USE_CONVEX:
                existing_by_link = convex_client.get_article_by_link(real_url)
                if existing_by_link:
                    titles_seen_this_run.add(normalized_title)
                    stats["duplicates_link"] += 1
                    continue
            else:
                cur.execute("SELECT id FROM \"Article\" WHERE link = %s", (real_url,))
                if cur.fetchone():
                    titles_seen_this_run.add(normalized_title)
                    stats["duplicates_link"] += 1
                    continue

            # 4. Récupération Meta et Insertion
            print(f"    [+] Nouveau ({feed['name']}): {title[:60]}...")
            titles_seen_this_run.add(normalized_title)
            
            time.sleep(random.uniform(0.3, 0.8))
            
            # Si le titre semble corrompu (cas DNA), on demande à fetch_content_data de le récupérer
            needs_title_fix = title.startswith('$') or "TitleNoTags" in title
            img, desc, fetched_title, caption = fetch_content_data(real_url, fetch_title=needs_title_fix)
            
            if needs_title_fix and fetched_title:
                print(f"      [ℹ️] Titre corrigé: {fetched_title[:50]}...")
                title = fetched_title

            # Doublon image : SQL uniquement. Convex s'en remet au dédup by_link.
            if img and not USE_CONVEX:
                pub_date = parsedate_to_datetime(pub_date_str)
                cur.execute("SELECT id FROM \"Article\" WHERE \"imageUrl\" = %s AND \"publishedAt\"::date = %s::date", (img, pub_date.date()))
                if cur.fetchone():
                    continue

            try:
                if USE_CONVEX:
                    # Nouvel article : on génère un UUID Supabase frais (nécessaire
                    # pour joindre tags/images côté Convex) puis upsert par link.
                    import uuid as uuid_mod
                    supabase_id = str(uuid_mod.uuid4())
                    row = {
                        "title": title,
                        "link": real_url,
                        "imageUrl": img,
                        "imageCaption": caption,
                        "source": source,
                        "description": desc,
                        "publishedAt": int(parsedate_to_datetime(pub_date_str).timestamp() * 1000),
                        "updatedAt": int(time.time() * 1000),
                        "supabaseId": supabase_id,
                    }
                    convex_client.upsert_article(row)
                    article_id = supabase_id
                else:
                    cur.execute("""
                        INSERT INTO "Article" (id, title, link, "imageUrl", "imageCaption", source, description, "publishedAt", "updatedAt")
                        VALUES (gen_random_uuid(), %s, %s, %s, %s, %s, %s, %s, NOW())
                        RETURNING id
                    """, (title, real_url, img, caption, source, desc, parsedate_to_datetime(pub_date_str)))
                    article_row = cur.fetchone()
                    article_id = article_row[0] if article_row else None
                
                # Détection et assignation automatique des tags
                if article_id and tags:
                    matched_tag_ids = detect_tags(title, desc, tags)
                    if matched_tag_ids:
                        assign_tags_to_article(cur, article_id, matched_tag_ids)
                        tag_names = [t['name'] for t in tags if t['id'] in matched_tag_ids]
                        print(f"      [🏷️] Tags: {', '.join(tag_names)}")
                
                if not USE_CONVEX:
                    conn.commit()
                new_count += 1
                stats["inserted_articles"].append({"title": title, "link": real_url, "source": source})
            except Exception as e:
                if not USE_CONVEX:
                    conn.rollback()
                print(f"      [!] Erreur insertion: {e}")

    print(f"\n[*] Terminé. {new_count} articles ajoutés au total.")
    
    # Enregistrement du log en base de données
    try:
        finished_at = datetime.now()
        status = "SUCCESS" if stats["google_decode_errors"] == 0 else "WARNING"
        if new_count == 0 and stats["total_rss_items"] == 0: status = "ERROR" # Si aucun item RSS trouvé (problème réseau ?)

        details = json.dumps(stats)
        
        if USE_CONVEX:
            convex_client.insert_scraping_log(
                started_at=start_time,
                finished_at=finished_at,
                status=status,
                articles_count=stats["total_rss_items"],
                success_count=new_count,
                error_count=stats["google_decode_errors"],
                details=details,
            )
        else:
            cur.execute("""
                INSERT INTO "ScrapingLog" (id, "startedAt", "finishedAt", status, "articlesCount", "successCount", "errorCount", details)
                VALUES (gen_random_uuid(), %s, %s, %s, %s, %s, %s, %s::jsonb)
            """, (start_time, finished_at, status, stats["total_rss_items"], new_count, stats["google_decode_errors"], details))
            conn.commit()
        print("[*] Log sauvegardé en DB.")
    except Exception as e:
        print(f"[!] Erreur sauvegarde log: {e}")
        if not USE_CONVEX and conn:
            conn.rollback()

    if cur:
        cur.close()
    if conn:
        conn.close()

if __name__ == "__main__":
    main()