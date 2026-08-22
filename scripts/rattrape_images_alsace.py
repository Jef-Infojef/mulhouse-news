#!/usr/bin/env python3
"""Script de rattrapage des images manquantes pour les articles L'Alsace (lalsace.fr).

Ce script :
1. Recherche les articles lalsace.fr sans `imageUrl` dans la base PostgreSQL.
2. Télécharge la page web de chaque article via un pool de threads.
3. Extrait l'URL de l'image (og:image, twitter:image, CDN L'Alsace) et la légende si disponible.
4. Met à jour la base de données PostgreSQL immédiatement.

Usage :
    # Traiter les articles récents de 2026 :
    python scripts/rattrape_images_alsace.py --year 2026

    # Traiter les 500 premiers articles sans image :
    python scripts/rattrape_images_alsace.py --limit 500

    # Mode test (sans écriture en base) :
    python scripts/rattrape_images_alsace.py --dry-run --limit 20

    # Traiter l'ensemble avec 10 workers :
    python scripts/rattrape_images_alsace.py --workers 10
"""

from __future__ import annotations

import argparse
import html
import json
import os
import re
import sys
import threading
import time
import urllib.parse
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

from bs4 import BeautifulSoup
from curl_cffi import requests as curl_requests
from dotenv import load_dotenv

# Chargement configuration
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(SCRIPT_DIR)
load_dotenv(os.path.join(PROJECT_DIR, ".env.local"))
load_dotenv(os.path.join(PROJECT_DIR, ".env"))

CDN_OK = re.compile(r"^https?://cdn-s-www\.lalsace\.fr/images/", re.I)
UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
)
CHECKPOINT_FILE = os.path.join(PROJECT_DIR, ".rattrape_images_checkpoint.json")

OG_IMAGE_RES = [
    re.compile(r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\'](.*?)["\']', re.I | re.S),
    re.compile(r'<meta[^>]+content=["\'](https?://[^"\']+?)["\'][^>]+property=["\']og:image["\']', re.I | re.S),
    re.compile(r'<meta[^>]+name=["\']twitter:image["\'][^>]+content=["\'](.*?)["\']', re.I | re.S),
    re.compile(r'<meta[^>]+content=["\'](https?://[^"\']+?)["\'][^>]+name=["\']twitter:image["\']', re.I | re.S),
]


def get_pg_connection():
    import psycopg2

    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        raise RuntimeError("DATABASE_URL absente dans .env/.env.local")
    if "?" in db_url:
        base, query = db_url.split("?", 1)
        params = urllib.parse.parse_qs(query)
        clean_params = {}
        if "sslmode" in params:
            clean_params["sslmode"] = params["sslmode"][0]
        db_url = base + ("?" + urllib.parse.urlencode(clean_params) if clean_params else "")
    return psycopg2.connect(db_url)


def norm_url(u: str) -> str:
    return html.unescape(u.strip())


def fetch_article_image(link: str, timeout: float = 15.0) -> tuple[str | None, str | None, str | None]:
    """Retourne (image_url, image_caption, error_message)."""
    last_err = "Inconnu"
    for attempt in range(3):
        try:
            resp = curl_requests.get(
                link, timeout=timeout, impersonate="chrome110", headers={"User-Agent": UA}
            )
            if resp.status_code == 200:
                html_text = resp.text
                img_url = None

                # 1. Regex meta tags
                for regex in OG_IMAGE_RES:
                    m = regex.search(html_text)
                    if m:
                        candidate = norm_url(m.group(1))
                        if candidate.startswith("http") and CDN_OK.match(candidate):
                            img_url = candidate
                            break

                # 2. Fallback BeautifulSoup si non trouvé
                caption = None
                if not img_url:
                    soup = BeautifulSoup(html_text, "html.parser")
                    for img in soup.find_all("img"):
                        src = img.get("src") or img.get("data-src")
                        if src and CDN_OK.match(src):
                            img_url = norm_url(src)
                            alt = img.get("alt")
                            if alt and len(alt.strip()) > 3:
                                caption = alt.strip()
                            break

                if img_url:
                    return img_url, caption, None
                return None, None, "Pas d'image CDN trouvée sur la page"

            if resp.status_code in (404, 410):
                return None, None, f"HTTP {resp.status_code} (Article indisponible)"
            return None, None, f"HTTP {resp.status_code}"
        except Exception as exc:
            last_err = f"Erreur réseau: {exc}"
            time.sleep(1.0 * (attempt + 1))
    return None, None, last_err


def fmt_eta(seconds: float) -> str:
    seconds = int(seconds)
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    return f"{h}h{m:02d}m{s:02d}s" if h else f"{m}m{s:02d}s"


def main():
    parser = argparse.ArgumentParser(
        description="Rattrapage des images manquantes pour les articles L'Alsace"
    )
    parser.add_argument("--dry-run", action="store_true", help="Scanne sans enregistrer en base")
    parser.add_argument("--limit", type=int, default=0, help="Nombre max d'articles à traiter (0 = tous)")
    parser.add_argument("--year", type=int, default=0, help="Filtrer par année de publication (ex: 2026)")
    parser.add_argument("--workers", type=int, default=8, help="Nombre de requêtes simultanées (défaut: 8)")
    parser.add_argument("--timeout", type=float, default=15.0, help="Timeout HTTP en secondes (défaut: 15s)")
    parser.add_argument("--reprendre", action="store_true", help="Reprendre à partir du dernier checkpoint")
    args = parser.parse_args()

    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

    print("=" * 70)
    print(" 📰 SCAN & RATTRAPAGE DES IMAGES - L'ALSACE (lalsace.fr)")
    print("=" * 70)

    try:
        conn = get_pg_connection()
        cur = conn.cursor()
    except Exception as e:
        print(f"❌ Erreur de connexion PostgreSQL : {e}")
        sys.exit(1)

    query = """
        SELECT id, link, title, "publishedAt"
        FROM "Article"
        WHERE (link LIKE '%lalsace.fr%' OR source ILIKE '%alsace%')
          AND ("imageUrl" IS NULL OR "imageUrl" = '' OR "imageUrl" = 'null')
    """
    params = []
    if args.year > 0:
        query += " AND EXTRACT(YEAR FROM \"publishedAt\") = %s"
        params.append(args.year)

    query += ' ORDER BY "publishedAt" DESC;'
    cur.execute(query, tuple(params) if params else None)
    candidates = cur.fetchall()
    total_candidates = len(candidates)

    print(f"[*] Articles sans image trouvés en base : {total_candidates}")
    if args.year > 0:
        print(f"[*] Filtre année : {args.year}")

    from_index = 0
    if args.reprendre and os.path.exists(CHECKPOINT_FILE):
        try:
            with open(CHECKPOINT_FILE, "r", encoding="utf-8") as f:
                chk = json.load(f)
                from_index = int(chk.get("done", 0))
                print(f"[*] Checkpoint actif : reprise à partir de l'article #{from_index}")
        except Exception:
            pass

    if from_index > 0:
        candidates = candidates[from_index:]
    if args.limit > 0:
        candidates = candidates[: args.limit]

    total_to_process = len(candidates)
    if total_to_process == 0:
        print("✅ Aucun article à traiter.")
        conn.close()
        return

    print(f"[*] Lancement du traitement sur {total_to_process} articles avec {args.workers} workers...")
    if args.dry_run:
        print("⚠️ Mode --dry-run actif : aucune modification en base de données.")

    done = 0
    fixed = 0
    not_found = 0
    errors = 0
    start_time = datetime.now()
    lock = threading.Lock()

    def update_article_db(article_id: str, img_url: str, caption: str | None):
        try:
            db_conn = get_pg_connection()
            c = db_conn.cursor()
            if caption:
                c.execute(
                    """
                    UPDATE "Article"
                    SET "imageUrl" = %s, "imageCaption" = %s, "updatedAt" = NOW()
                    WHERE id = %s;
                """,
                    (img_url, caption, article_id),
                )
            else:
                c.execute(
                    """
                    UPDATE "Article"
                    SET "imageUrl" = %s, "updatedAt" = NOW()
                    WHERE id = %s;
                """,
                    (img_url, article_id),
                )
            db_conn.commit()
            db_conn.close()
        except Exception as err:
            with lock:
                print(f"    [!] Erreur écriture DB ({article_id}): {err}")

    def process_item(item):
        art_id, link, title, pub_date = item
        img_url, caption, err = fetch_article_image(link, timeout=args.timeout)
        if img_url:
            if not args.dry_run:
                update_article_db(art_id, img_url, caption)
            return True, img_url, title
        return False, err, title

    with ThreadPoolExecutor(max_workers=max(1, args.workers)) as pool:
        future_map = {pool.submit(process_item, c): c for c in candidates}
        for future in as_completed(future_map):
            done += 1
            success, result_info, title = future.result()
            with lock:
                if success:
                    fixed += 1
                    clean_title = (title[:45] + "...") if title and len(title) > 45 else (title or "")
                    print(f"  [+] ({fixed}/{done}) Image trouvée: {result_info[:65]}... | {clean_title}")
                else:
                    if "HTTP" in str(result_info) or "Erreur réseau" in str(result_info):
                        errors += 1
                    else:
                        not_found += 1

            if done % 20 == 0 or done == total_to_process:
                elapsed = (datetime.now() - start_time).total_seconds()
                rate = done / elapsed if elapsed > 0 else 0.0
                rem = (total_to_process - done) / rate if rate > 0 else 0
                print(
                    f"--- Progression: [{done}/{total_to_process}] "
                    f"| Trouvées: {fixed} | Introuvables: {not_found} | Erreurs: {errors} "
                    f"| {rate:.1f} art/s | ETA: {fmt_eta(rem)} ---"
                )

                # Sauvegarde checkpoint
                try:
                    with open(CHECKPOINT_FILE, "w", encoding="utf-8") as f:
                        json.dump({"done": from_index + done, "timestamp": datetime.now().isoformat()}, f)
                except Exception:
                    pass

    conn.close()
    elapsed_total = (datetime.now() - start_time).total_seconds()
    print("\n" + "=" * 70)
    print(f"🏁 TERMINÉ en {fmt_eta(elapsed_total)}")
    print(f"   • Articles traités   : {done}")
    print(f"   • Images récupérées  : {fixed}")
    print(f"   • Pages sans image   : {not_found}")
    print(f"   • Erreurs réseau/404 : {errors}")
    print("=" * 70)


if __name__ == "__main__":
    main()
