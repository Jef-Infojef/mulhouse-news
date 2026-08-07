"""Scraping des articles Le Monde concernant Mulhouse via leur page de recherche."""
import argparse
import os
import sys
import time
import random
import html
import re
import json
from datetime import datetime
from urllib.parse import urlparse

import psycopg2
from dotenv import load_dotenv
from curl_cffi import requests
from bs4 import BeautifulSoup

# Fix encoding pour Windows
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

load_dotenv()
load_dotenv(".env.local")

DATABASE_URL = os.environ.get("DATABASE_URL")


def get_db_connection():
    if not DATABASE_URL:
        raise Exception("DATABASE_URL non définie")
    clean_url = DATABASE_URL.replace("?pgbouncer=true", "").replace("&pgbouncer=true", "")
    return psycopg2.connect(clean_url)


def scrape_search_page(page_num: int) -> list[dict]:
    """Récupère les articles d'une page de recherche Le Monde."""
    url = f'https://www.lemonde.fr/recherche/?search_keywords=mulhouse&page={page_num}'

    try:
        time.sleep(random.uniform(5.0, 10.0))  # Délai plus long pour éviter le rate limiting
        resp = requests.get(url, timeout=30, impersonate="chrome120")

        if resp.status_code != 200:
            print(f"  [!] Erreur HTTP {resp.status_code}")
            return []

        soup = BeautifulSoup(resp.text, 'html.parser')
        articles = []

        # Patterns à exclure
        exclude_patterns = [
            '/guides-d-achat/', '/video/', '/podcast/', '/services/', '/abonnes/',
            '/meteo/', '/resultats-', '/archives/', '/logement/', '/immobilier/',
            '/partenaire/', '/publicite/'
        ]

        for a in soup.find_all('a', href=True):
            href = a['href']

            # Skip URLs exclues
            if any(p in href for p in exclude_patterns):
                continue

            # Ne garder que les vrais articles
            if '/article/' not in href:
                continue

            # Nettoyer l'URL
            if href.startswith('//'):
                href = 'https:' + href
            elif not href.startswith('http'):
                href = 'https://www.lemonde.fr' + href

            # Extraire le titre (nettoyer les préfixes comme "DécryptageArticle réservé à nos abonnés")
            title = a.get_text(strip=True)
            title = re.sub(r'^(Décryptage|Portrait|Reportage|Récit|Exclusivité|Analyse|Edito)[\s:]+', '', title)
            title = title.strip()

            if title and len(title) > 15:
                articles.append({
                    'title': title[:200],
                    'url': href
                })

        # Dédupliquer
        seen = set()
        unique = []
        for art in articles:
            if art['url'] not in seen:
                seen.add(art['url'])
                unique.append(art)

        return unique

    except Exception as e:
        print(f"  [!] Erreur: {e}")
        return []


def fetch_article_content(url: str) -> dict:
    """Récupère le contenu complet d'un article Le Monde."""
    result = {
        "content": None,
        "image_url": None,
        "image_caption": None,
        "description": None,
        "accessible": False,
        "paywall": False,
    }

    try:
        time.sleep(random.uniform(0.5, 1.5))

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "fr-FR,fr;q=0.9,en;q=0.8",
        }

        resp = requests.get(url, headers=headers, timeout=25, impersonate="chrome120", allow_redirects=True)

        if resp.status_code != 200:
            return result

        soup = BeautifulSoup(resp.text, 'html.parser')

        # Vérifier si paywall
        title_tag = soup.find('title')
        if title_tag and ('abonnes' in title_tag.text.lower() or 'paywall' in resp.text.lower()):
            result["paywall"] = True

        result["accessible"] = True

        # og:image
        og_image = soup.find('meta', property='og:image')
        if og_image and og_image.get('content'):
            result["image_url"] = html.unescape(og_image['content']).strip()

        # og:description
        og_desc = soup.find('meta', property='og:description')
        if og_desc and og_desc.get('content'):
            result["description"] = html.unescape(og_desc['content']).strip()

        # Contenu de l'article
        article = soup.find('article')
        if article:
            paragraphs = []
            for p in article.find_all('p'):
                text = p.get_text(' ', strip=True)
                if len(text) > 50:
                    paragraphs.append(text)

            if paragraphs:
                # Dédupliquer tout en gardant l'ordre
                seen = set()
                unique_paras = []
                for p in paragraphs:
                    if p.lower() not in seen:
                        seen.add(p.lower())
                        unique_paras.append(p)

                if unique_paras:
                    result["content"] = "\n\n".join(unique_paras)

        # Légende image
        if result["image_url"]:
            figure = soup.find('figure')
            if figure:
                figcaption = figure.find('figcaption')
                if figcaption:
                    result["image_caption"] = figcaption.get_text(' ', strip=True)

    except Exception as e:
        print(f"    [!] Erreur fetch: {e}")

    return result


def main():
    parser = argparse.ArgumentParser(description="Scraping Le Monde - Mulhouse via recherche directe")
    parser.add_argument("--pages", type=int, default=1, help="Nombre de pages à scraper")
    parser.add_argument("--start-page", type=int, default=1, help="Page de départ")
    parser.add_argument("--dry-run", action="store_true", help="Ne pas insérer en base")
    parser.add_argument("--no-fetch", action="store_true", help="Ne pas récupérer le contenu des articles")
    parser.add_argument("--fetch-only", action="store_true", help="Enrichir les articles Le Monde existants sans contenu")
    args = parser.parse_args()

    print(f"[*] Le Monde Search Scraper - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"[*] Pages: {args.start_page} à {args.start_page + args.pages - 1}")

    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
    except Exception as e:
        print(f"[!] Erreur connexion DB: {e}")
        return

    if args.fetch_only:
        # Mode enrichment: enrichir les articles Le Monde existants sans contenu
        print("\n--- Mode: Enrichir articles existants ---")
        cur.execute("""
            SELECT id, title, link
            FROM "Article"
            WHERE link LIKE '%%lemonde.fr%%'
            AND (content IS NULL OR LENGTH(content) < 100)
            ORDER BY "publishedAt" DESC
        """)
        articles = cur.fetchall()
        print(f"[*] {len(articles)} articles à enrichir")

        success = 0
        for i, (art_id, title, link) in enumerate(articles, 1):
            print(f"[{i}/{len(articles)}] {title[:50]}...")
            content = fetch_article_content(link)

            if content["accessible"] and content["content"]:
                try:
                    cur.execute("""
                        UPDATE "Article"
                        SET content = %s,
                            "imageUrl" = COALESCE(%s, "imageUrl"),
                            "imageCaption" = COALESCE(%s, "imageCaption"),
                            description = COALESCE(%s, description),
                            "updatedAt" = NOW()
                        WHERE id = %s
                    """, (
                        content["content"],
                        content["image_url"],
                        content["image_caption"],
                        content["description"],
                        art_id
                    ))
                    conn.commit()
                    success += 1
                    print(f"    [OK] Enrichi")
                except Exception as e:
                    conn.rollback()
                    print(f"    [!] Erreur: {e}")
            else:
                status = "paywall" if content["paywall"] else "inaccessible"
                print(f"    [!] {status}")

        print(f"\n[*] Terminé: {success}/{len(articles)} enrichis")
        cur.close()
        conn.close()
        return

    # Mode: découvrir de nouveaux articles
    total_found = 0
    total_new = 0
    total_existing = 0
    seen_urls = set()

    for page in range(args.start_page, args.start_page + args.pages):
        print(f"\n--- Page {page} ---")
        articles = scrape_search_page(page)
        print(f"[*] {len(articles)} articles trouvés")
        total_found += len(articles)

        for art in articles:
            url = art['url']
            title = art['title']

            if url in seen_urls:
                continue
            seen_urls.add(url)

            # Vérifier si déjà en base
            cur.execute('SELECT id FROM "Article" WHERE link = %s', (url,))
            if cur.fetchone():
                total_existing += 1
                continue

            print(f"    [+] {title[:60]}...")

            if args.no_fetch or args.dry_run:
                content_data = {
                    "image_url": None,
                    "image_caption": None,
                    "description": None,
                    "content": None,
                    "accessible": False,
                }
            else:
                content_data = fetch_article_content(url)

            if args.dry_run:
                print(f"      [DRY] URL: {url[:60]}...")
                total_new += 1
                continue

            # Insérer en base
            try:
                cur.execute("""
                    INSERT INTO "Article" (id, title, link, "imageUrl", "imageCaption", source, description, "publishedAt", "updatedAt")
                    VALUES (gen_random_uuid(), %s, %s, %s, %s, %s, %s, NOW(), NOW())
                    ON CONFLICT (link) DO NOTHING
                    RETURNING id
                """, (
                    title,
                    url,
                    content_data.get("image_url"),
                    content_data.get("image_caption"),
                    "Le Monde",
                    content_data.get("description"),
                ))
                result = cur.fetchone()
                if result:
                    conn.commit()
                    total_new += 1
                    print(f"      [OK] Inséré")
                else:
                    conn.rollback()
                    total_existing += 1
            except Exception as e:
                conn.rollback()
                print(f"      [!] Erreur: {e}")

    print(f"\n[*] Résumé:")
    print(f"    Trouvés: {total_found}")
    print(f"    Nouveaux: {total_new}")
    print(f"    Déjà en base: {total_existing}")

    cur.close()
    conn.close()
    print("[*] Terminé")


if __name__ == "__main__":
    main()
