#!/usr/bin/env python3
"""Script de rattrapage et correction des accents / titres slugifiés pour les articles L'Alsace.

Ce script :
1. Détecte les articles dont les titres sont sans accents, slugifiés ou mal encodés.
2. Télécharge la page web de chaque article via un pool de threads parallèles.
3. Extrait le véritable titre officiel (`og:title`, `<title>`, `<h1>`) avec accents et ponctuation français.
4. Nettoie les suffixes de journal (" - L'Alsace", " | L'Alsace", etc.) et met à jour PostgreSQL.

Usage :
    # Corriger les titres d'une année spécifique (ex: 2025) :
    python scripts/rattrape_titres_accents.py --year 2025

    # Traiter un premier lot (ex: 500 articles) :
    python scripts/rattrape_titres_accents.py --limit 500

    # Mode test (affiche les corrections sans écrire en base) :
    python scripts/rattrape_titres_accents.py --dry-run --limit 20

    # Lancer l'ensemble avec 12 workers parallèles :
    python scripts/rattrape_titres_accents.py --workers 12

    # Reprendre après interruption :
    python scripts/rattrape_titres_accents.py --reprendre
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
import unicodedata
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

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
)
CHECKPOINT_FILE = os.path.join(PROJECT_DIR, ".rattrape_titres_checkpoint.json")

ACCENTED_CHARS = set("àâäçéèêëîïôöùûüÿœæÀÂÄÇÉÈÊËÎÏÔÖÙÛÜŒÆ")

OG_TITLE_RES = [
    re.compile(rb'<meta[^>]+property=["\']og:title["\'][^>]+content=["\'](.*?)["\']', re.I | re.S),
    re.compile(rb'<meta[^>]+content=["\'](.*?)["\'][^>]+property=["\']og:title["\']', re.I | re.S),
    re.compile(rb'<meta[^>]+name=["\']twitter:title["\'][^>]+content=["\'](.*?)["\']', re.I | re.S),
    re.compile(rb'<meta[^>]+content=["\'](.*?)["\'][^>]+name=["\']twitter:title["\']', re.I | re.S),
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


def needs_title_fix(title: str | None) -> bool:
    """Détecte avec précision si un titre nécessite d'être récupéré depuis la page."""
    if not title or title == "Sans titre":
        return True
    if "\ufffd" in title or "\ufffe" in title or "?" in title:
        return True
    
    # Présence d'artefacts typiques de slug (lettres isolées : "d abord", "l alsace", "j y", "n a")
    if re.search(r"\b[dlcjnms]\b\s+[a-z]", title, re.I):
        return True

    # Titre sans aucun accent français
    has_accents = any(c in ACCENTED_CHARS for c in title)
    if not has_accents:
        # Si sans ponctuation et sans majuscules internes, c'est un slug
        has_punctuation = bool(re.search(r'[,:;«»"\'?!.]', title))
        has_multiple_caps = len(re.findall(r'[A-Z]', title)) >= 2
        if not has_punctuation and not has_multiple_caps:
            return True

    return False


def clean_title_text(raw_title: str) -> str:
    """Nettoie le titre (entités HTML, suffixes de journal, espaces insécables)."""
    t = html.unescape(raw_title.strip())
    t = t.replace("\u00a0", " ").replace("\u202f", " ")
    t = re.sub(r"\s*[-–—|]\s*(?:L'Alsace|lalsace\.fr|DNA|Dernières Nouvelles d'Alsace|ICI Alsace|France Bleu|M\+)\s*$", "", t, flags=re.I)
    t = re.sub(r"\s*\|\s*L'Alsace\s*$", "", t, flags=re.I)
    return t.strip()


def fetch_official_title(link: str, timeout: float = 15.0) -> tuple[str | None, str | None]:
    """Extrait le titre officiel depuis la page web."""
    last_err = "Inconnu"
    for attempt in range(3):
        try:
            resp = curl_requests.get(
                link, timeout=timeout, impersonate="chrome110", headers={"User-Agent": UA}
            )
            if resp.status_code == 200:
                raw_bytes = resp.content

                # 1. Extraction regex og:title / twitter:title
                for regex in OG_TITLE_RES:
                    m = regex.search(raw_bytes)
                    if m:
                        try:
                            title_candidate = m.group(1).decode("utf-8", errors="replace")
                            clean = clean_title_text(title_candidate)
                            if len(clean) > 3:
                                return clean, None
                        except Exception:
                            pass

                # 2. Fallback BeautifulSoup (h1 ou title)
                soup = BeautifulSoup(raw_bytes, "html.parser", from_encoding="utf-8")
                h1 = soup.find("h1")
                if h1:
                    clean = clean_title_text(h1.get_text(strip=True))
                    if len(clean) > 3:
                        return clean, None

                title_tag = soup.find("title")
                if title_tag:
                    clean = clean_title_text(title_tag.get_text(strip=True))
                    if len(clean) > 3:
                        return clean, None

                return None, "Aucun titre trouvé dans le HTML"

            if resp.status_code in (404, 410):
                return None, f"HTTP {resp.status_code} (Article indisponible)"
            return None, f"HTTP {resp.status_code}"
        except Exception as exc:
            last_err = f"Erreur réseau: {exc}"
            time.sleep(1.0 * (attempt + 1))
    return None, last_err


def fmt_eta(seconds: float) -> str:
    seconds = int(seconds)
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    return f"{h}h{m:02d}m{s:02d}s" if h else f"{m}m{s:02d}s"


def main():
    parser = argparse.ArgumentParser(
        description="Rattrapage des titres avec accents et typographie officielle pour L'Alsace"
    )
    parser.add_argument("--dry-run", action="store_true", help="Scanne sans enregistrer en base")
    parser.add_argument("--limit", type=int, default=0, help="Nombre max d'articles à traiter (0 = tous)")
    parser.add_argument("--year", type=int, default=0, help="Filtrer par année de publication (ex: 2025)")
    parser.add_argument("--workers", type=int, default=12, help="Nombre de requêtes simultanées (défaut: 12)")
    parser.add_argument("--timeout", type=float, default=15.0, help="Timeout HTTP en secondes (défaut: 15s)")
    parser.add_argument("--reprendre", action="store_true", help="Reprendre à partir du dernier checkpoint")
    args = parser.parse_args()

    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

    print("=" * 75)
    print(" ✍️  SCAN & RATTRAPAGE DES ACCENTS / TITRES - L'ALSACE (lalsace.fr)")
    print("=" * 75)

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
    """
    params = []
    if args.year > 0:
        query += ' AND EXTRACT(YEAR FROM "publishedAt") = %s'
        params.append(args.year)

    query += ' ORDER BY "publishedAt" DESC;'
    cur.execute(query, tuple(params) if params else None)
    all_articles = cur.fetchall()

    candidates = [a for a in all_articles if needs_title_fix(a[2])]
    total_candidates = len(candidates)

    print(f"[*] Articles totaux analysés en base : {len(all_articles)}")
    print(f"[*] Titres sans accents / slugifiés identifiés : {total_candidates}")
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
        print("✅ Aucun titre à corriger.")
        conn.close()
        return

    print(f"[*] Lancement du traitement sur {total_to_process} articles avec {args.workers} workers...")
    if args.dry_run:
        print("⚠️ Mode --dry-run actif : aucune modification en base de données.")

    done = 0
    fixed = 0
    identical = 0
    errors = 0
    start_time = datetime.now()
    lock = threading.Lock()

    def update_article_title(article_id: str, new_title: str):
        try:
            db_conn = get_pg_connection()
            c = db_conn.cursor()
            c.execute(
                """
                UPDATE "Article"
                SET "title" = %s, "updatedAt" = NOW()
                WHERE id = %s;
            """,
                (new_title, article_id),
            )
            db_conn.commit()
            db_conn.close()
        except Exception as err:
            with lock:
                print(f"    [!] Erreur écriture DB ({article_id}): {err}")

    def process_item(item):
        art_id, link, old_title, pub_date = item
        official_title, err = fetch_official_title(link, timeout=args.timeout)
        if official_title:
            if official_title != old_title:
                if not args.dry_run:
                    update_article_title(art_id, official_title)
                return "fixed", old_title, official_title
            return "identical", old_title, official_title
        return "error", old_title, err

    with ThreadPoolExecutor(max_workers=max(1, args.workers)) as pool:
        future_map = {pool.submit(process_item, c): c for c in candidates}
        for future in as_completed(future_map):
            done += 1
            status, old_t, new_t = future.result()
            with lock:
                if status == "fixed":
                    fixed += 1
                    old_display = (old_t[:35] + "...") if old_t and len(old_t) > 35 else (old_t or "")
                    new_display = (new_t[:45] + "...") if new_t and len(new_t) > 45 else (new_t or "")
                    print(f"  [+] ({fixed}/{done}) {old_display} ➔ {new_display}")
                elif status == "identical":
                    identical += 1
                else:
                    errors += 1

            if done % 25 == 0 or done == total_to_process:
                elapsed = (datetime.now() - start_time).total_seconds()
                rate = done / elapsed if elapsed > 0 else 0.0
                rem = (total_to_process - done) / rate if rate > 0 else 0
                print(
                    f"--- Progression: [{done}/{total_to_process}] "
                    f"| Corrigés: {fixed} | Identiques: {identical} | Erreurs: {errors} "
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
    print("\n" + "=" * 75)
    print(f"🏁 TERMINÉ en {fmt_eta(elapsed_total)}")
    print(f"   • Articles traités   : {done}")
    print(f"   • Titres corrigés    : {fixed}")
    print(f"   • Déjà conformes     : {identical}")
    print(f"   • Erreurs réseau/404 : {errors}")
    print("=" * 75)


if __name__ == "__main__":
    main()
