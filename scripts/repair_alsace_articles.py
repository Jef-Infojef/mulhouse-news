"""Rattrapage des articles L'Alsace incomplets (source « (archive) », titre slug, photo manquante).

Deux populations, une seule passe et une seule requête HTTP par article :

  1. les articles insérés sous l'ancien libellé `L'Alsace (archive)` — un
     doublon de source créé par le canal de découverte (sitemap) alors qu'il
     s'agit du même journal que le flux RSS. Ils sont ramenés sous `L'Alsace` ;
  2. les articles déjà sous `L'Alsace` mais sans `imageUrl` — reliquat des
     insertions faites avant que `scrape_alsace_archive.py` ne lise la page.

Pour chacun, la page lalsace.fr est ouverte et `parse_ebra_page_meta` en tire
le vrai titre accentué, la description, l'`og:image` (rejet du placeholder
`ALS_placeholder.png` et de tout ce qui n'est pas le CDN EBRA), la légende,
l'auteur et la rubrique. Rien n'est écrasé par du vide : un champ non trouvé
laisse la valeur existante intacte.

Deux ordres de traitement :

  • `--order recent` (défaut) : les plus récents d'abord, c'est-à-dire ce que la
    home affiche. Idéal pour un run plafonné ;
  • `--order source` : balayage par source (index `by_source`), pour écouler le
    stock d'archive — là où l'ordre par date parcourt toute la table.

Aucun checkpoint : la reprise est structurelle. Un article réparé quitte la
population qu'il occupait (sa source change, ou son `imageUrl` se remplit), donc
il disparaît de lui-même des candidats du run suivant. Un index de reprise
figé, lui, ferait sauter du travail à mesure que la liste se raccourcit.

Usage :
    python scripts/repair_alsace_articles.py --dry-run --limit 50   # sonde
    python scripts/repair_alsace_articles.py --limit 300            # la home d'abord
    python scripts/repair_alsace_articles.py --order source --only-legacy --limit 5000
    python scripts/repair_alsace_articles.py --env C:/dev/MulhouseGPT/.env.local

Backend : Convex uniquement (CONVEX_DEPLOY_KEY + NEXT_PUBLIC_CONVEX_URL). Le
script affiche sa progression et s'arrête seul : fin de liste, `--limit`
atteinte, ou 30 échecs réseau consécutifs.
"""

from __future__ import annotations

import argparse
import os
import random
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

from curl_cffi import requests as curl_requests
from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import convex_client
from scrape_utils import parse_ebra_page_meta

load_dotenv(".env.local")
load_dotenv()

SOURCE = "L'Alsace"
SOURCE_LEGACY = "L'Alsace (archive)"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"
MAX_CONSECUTIVE_NETWORK_FAILURES = 30


def fetch_page(link: str, timeout: float) -> tuple[str | None, str | None]:
    """(html, erreur). Trois essais avec backoff sur erreur réseau/5xx."""
    err = "inconnue"
    for attempt in range(3):
        try:
            resp = curl_requests.get(
                link, timeout=timeout, impersonate="chrome110", headers={"User-Agent": UA}
            )
            if resp.status_code == 200:
                return resp.text, None
            # 404/410 : article retiré du site, inutile d'insister.
            if resp.status_code in (404, 410):
                return None, f"HTTP {resp.status_code}"
            err = f"HTTP {resp.status_code}"
        except Exception as exc:  # noqa: BLE001 — erreur réseau transitoire
            err = f"réseau: {exc}"
        time.sleep(1.5 * (attempt + 1))
    return None, err


def list_candidates_recent_first(max_articles: int) -> list[dict]:
    """À réparer, du plus récent au plus ancien (scrapers:getArticlesToRepairPage).

    C'est l'ordre utile : la home n'affiche que les articles récents, un run
    plafonné doit donc commencer par eux. La pagination s'arrête dès que
    `max_articles` est atteint, sans parcourir les ~100 000 articles d'archive.
    """
    rows = convex_client.get_articles_to_repair(
        [SOURCE, SOURCE_LEGACY], SOURCE_LEGACY, max_articles=max_articles
    )
    out = [
        {"link": r["link"], "needs_source": r["needsSource"], "needs_image": r["needsImage"]}
        for r in rows
    ]
    legacy = sum(1 for r in out if r["needs_source"])
    print(f"[*] {len(out)} articles à réparer ({legacy} sous « {SOURCE_LEGACY} », "
          f"{len(out) - legacy} déjà sous « {SOURCE} » mais sans photo)")
    return out


def list_candidates_by_source(only_legacy: bool) -> list[dict]:
    """Balayage exhaustif par source (index by_source), sans ordre de date.

    Pour le rattrapage de fond des ~100 000 articles d'archive : la pagination
    `by_source` ne lit que les documents concernés, là où l'ordre par date
    parcourt toute la table.
    """
    rows: list[dict] = []
    for link in convex_client.get_article_links(source=SOURCE_LEGACY):
        rows.append({"link": link, "needs_source": True, "needs_image": True})
    print(f"[*] {len(rows)} articles sous « {SOURCE_LEGACY} » à ramener sous « {SOURCE} »")

    if only_legacy:
        return rows

    before = len(rows)
    for art in convex_client.get_article_titles(source=SOURCE):
        if art.get("imageUrl"):
            continue
        rows.append({"link": art["link"], "needs_source": False, "needs_image": True})
    print(f"[*] {len(rows) - before} articles déjà sous « {SOURCE} » mais sans photo")
    return rows


def fmt_eta(seconds: float) -> str:
    seconds = int(seconds)
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    return f"{h}h{m:02d}m{s:02d}s" if h else f"{m}m{s:02d}s"


def build_patch(candidate: dict, html: str) -> dict:
    """Champs à écrire pour cet article — jamais de valeur vide en écrasement."""
    meta = parse_ebra_page_meta(html, candidate["link"])
    patch: dict = {"link": candidate["link"]}
    if candidate["needs_source"]:
        patch["source"] = SOURCE
    for field, meta_key in (
        ("title", "title"),
        ("description", "description"),
        ("imageUrl", "image_url"),
        ("imageCaption", "image_caption"),
        ("author", "author"),
        ("category", "category"),
    ):
        if meta[meta_key]:
            patch[field] = meta[meta_key]
    return patch


def main() -> None:
    parser = argparse.ArgumentParser(description="Rattrapage des articles L'Alsace incomplets")
    parser.add_argument("--dry-run", action="store_true", help="Sonde et affiche sans écrire")
    parser.add_argument("--limit", type=int, default=0, help="Plafonne le nombre d'articles traités (0 = illimité)")
    parser.add_argument("--only-legacy", action="store_true",
                        help="Ne traiter que la migration de source « (archive) » → « L'Alsace »")
    parser.add_argument("--order", choices=["recent", "source"], default="recent",
                        help="'recent' (défaut) : les plus récents d'abord, ce que voit la home. "
                             "'source' : balayage exhaustif par source pour le rattrapage de fond.")
    parser.add_argument("--workers", type=int, default=5, help="Threads parallèles (défaut 5)")
    parser.add_argument("--sleep", type=float, default=0.2, help="Pause par thread entre deux requêtes (s)")
    parser.add_argument("--timeout", type=float, default=30.0, help="Timeout HTTP par requête (s)")
    parser.add_argument("--env", type=str, default=None,
                        help="Fichier .env à charger EN PRIORITÉ (ex. celui du déploiement prod)")
    args = parser.parse_args()

    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:  # noqa: BLE001
        pass
    if args.env:
        load_dotenv(args.env, override=True)

    if not convex_client.use_convex():
        print("❌ Convex non configuré : définir CONVEX_DEPLOY_KEY et NEXT_PUBLIC_CONVEX_URL.")
        sys.exit(1)
    print(f"[*] Backend : Convex (cloud) — {convex_client.get_convex_url()}")

    if args.order == "recent":
        candidates = list_candidates_recent_first(args.limit)
    else:
        candidates = list_candidates_by_source(args.only_legacy)

    if args.limit:
        candidates = candidates[: args.limit]
    total = len(candidates)
    print(f"[*] {total} articles à traiter")
    if not total:
        return

    done = migrated = with_image = no_image = gone = network_err = 0
    consecutive_failures = 0
    lock = threading.Lock()
    start_time = datetime.now()

    def progress() -> None:
        elapsed = (datetime.now() - start_time).total_seconds()
        rate = done / elapsed if elapsed > 0 else 0.0
        remaining = (total - done) / rate if rate > 0 else float("inf")
        print(
            f"   [{done}/{total}] source migrée: {migrated} | photo trouvée: {with_image} "
            f"| sans photo: {no_image} | page disparue: {gone} | erreurs réseau: {network_err} "
            f"| débit {rate:.1f}/s | ETA {fmt_eta(remaining)}"
        )

    def process(candidate: dict) -> None:
        nonlocal done, migrated, with_image, no_image, gone, network_err, consecutive_failures
        html, err = fetch_page(candidate["link"], args.timeout)
        time.sleep(args.sleep + random.uniform(0, 0.2))

        patch = build_patch(candidate, html) if html else None
        # Page injoignable : on migre quand même la source, sinon l'article
        # resterait indéfiniment dans une source fantôme.
        if patch is None and candidate["needs_source"]:
            patch = {"link": candidate["link"], "source": SOURCE}

        with lock:
            if html:
                consecutive_failures = 0
                if patch and patch.get("imageUrl"):
                    with_image += 1
                else:
                    no_image += 1
            elif err and err.startswith("HTTP 4"):
                consecutive_failures = 0
                gone += 1
            else:
                consecutive_failures += 1
                network_err += 1

        if patch and not args.dry_run:
            try:
                patch["updatedAt"] = int(time.time() * 1000)
                convex_client.upsert_article(patch)
                if candidate["needs_source"]:
                    with lock:
                        migrated += 1
            except convex_client.ConvexError as exc:
                print(f"    [!] Écriture refusée ({candidate['link']}): {str(exc)[:120]}")
        elif patch and args.dry_run and candidate["needs_source"]:
            with lock:
                migrated += 1

        with lock:
            done += 1
            if done % 25 == 0 or done == total:
                progress()

    with ThreadPoolExecutor(max_workers=max(1, args.workers)) as pool:
        futures = [pool.submit(process, c) for c in candidates]
        for future in as_completed(futures):
            future.result()
            if consecutive_failures >= MAX_CONSECUTIVE_NETWORK_FAILURES:
                print(f"\n❌ {MAX_CONSECUTIVE_NETWORK_FAILURES} échecs réseau consécutifs — arrêt.")
                for pending in futures:
                    pending.cancel()
                break

    print(
        f"\n[*] {'SONDE' if args.dry_run else 'TERMINÉ'} : {done} traités, "
        f"{migrated} ramenés sous « {SOURCE} », {with_image} avec photo, "
        f"{no_image} sans photo exploitable, {gone} pages disparues, {network_err} erreurs réseau."
    )


if __name__ == "__main__":
    main()
