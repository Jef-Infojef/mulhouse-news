"""Backfill des images manquantes (og:image) pour les articles lalsace.fr.

Les inserts d'archive sitemap n'ont pas toujours de photo : imageUrl et r2Url
sont vides en Convex, donc les citations RAG s'affichent sans illustration
alors que la page a une `og:image`.

Ce script :
  1. liste les articles lalsace.fr sans imageUrl ni r2Url ;
  2. récupère la page et lit `og:image` (pool de threads) ;
  3. ne garde que les images du CDN L'Alsace (cdn-s-www.lalsace.fr) ;
  4. met à jour via `scrapers:upsertArticle` (patch par link).

Usage :
    python scripts/backfill_missing_images.py --env C:/dev/MulhouseGPT/.env.local
    python scripts/backfill_missing_images.py --env … --dry-run          # sonde
    python scripts/backfill_missing_images.py --env … --limit 50         # plafonner
    python scripts/backfill_missing_images.py --env … --reprendre        # checkpoint

Backend : Convex uniquement. Progression auto-affichée ; arrêt seul en fin de
liste ou après 30 échecs réseau consécutifs.
"""

from __future__ import annotations

import argparse
import html
import json
import random
import re
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

from curl_cffi import requests as curl_requests
from dotenv import load_dotenv

import convex_client

load_dotenv(".env.local")
load_dotenv()

SOURCE_DOMAIN = "lalsace.fr"
CDN_OK = re.compile(r"^https://cdn-s-www\.lalsace\.fr/images/", re.I)
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"
CHECKPOINT_FILE = ".backfill_images_progress.json"

OG_IMAGE_RES = [
    re.compile(r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\'](.*?)["\']', re.I | re.S),
    re.compile(r'<meta[^>]+content=["\'](https?://[^"\']+?)["\'][^>]+property=["\']og:image["\']', re.I | re.S),
]

MAX_CONSECUTIVE_NETWORK_FAILURES = 30


def norm_url(u: str) -> str:
    """URL absolue, &amp; dé-échappé."""
    return html.unescape(u.strip())


def fetch_og_image(link: str, timeout: float) -> tuple[str | None, str | None]:
    """Retourne (og_image, erreur). og_image=None si absent/indigne de confiance."""
    err = "inconnue"
    for attempt in range(3):
        try:
            resp = curl_requests.get(
                link, timeout=timeout, impersonate="chrome110", headers={"User-Agent": UA}
            )
            if resp.status_code == 200:
                m = next((m for m in (r.search(resp.text) for r in OG_IMAGE_RES) if m), None)
                if not m:
                    return None, "og:image absent"
                img = norm_url(m.group(1))
                if not img.startswith("http"):
                    return None, "og:image relatif"
                if not CDN_OK.match(img):
                    return None, "hors CDN lalsace"
                return img, None
            if resp.status_code in (404, 410):
                return None, f"HTTP {resp.status_code}"
            return None, f"HTTP {resp.status_code}"
        except Exception as exc:  # noqa: BLE001 — erreur réseau transitoire
            err = f"réseau: {exc}"
            time.sleep(1.5 * (attempt + 1))
    return None, err


def list_candidates() -> list[str]:
    """Liens lalsace.fr sans aucune image, via pagination getArticlesPage."""
    rows: list[str] = []
    cursor: str | None = None
    page = 0
    while True:
        res = convex_client._call(
            "news_bridge:getArticlesPage",
            {"cursor": cursor, "limit": 500},
            mutation=False,
        )
        for a in res["articles"]:
            link = a.get("link") or ""
            if SOURCE_DOMAIN not in link:
                continue
            if a.get("imageUrl") or a.get("r2Url"):
                continue
            rows.append(link)
        page += 1
        if page % 20 == 0:
            print(f"[*] … {page} pages, {len(rows)} candidats")
        if res.get("isDone") or not res.get("cursor"):
            break
        cursor = res["cursor"]
    return rows


def fmt_eta(seconds: float) -> str:
    seconds = int(seconds)
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    return f"{h}h{m:02d}m{s:02d}s" if h else f"{m}m{s:02d}s"


def main() -> None:
    parser = argparse.ArgumentParser(description="Backfill og:image des articles lalsace.fr sans photo")
    parser.add_argument("--dry-run", action="store_true", help="Sonde sans mettre à jour")
    parser.add_argument("--limit", type=int, default=0, help="Plafonne le nombre d'articles traités")
    parser.add_argument("--from", type=int, default=0, dest="from_index", help="Ignore les N premiers candidats")
    parser.add_argument("--reprendre", action="store_true", help="Reprend depuis le checkpoint")
    parser.add_argument("--workers", type=int, default=5, help="Threads parallèles (défaut 5)")
    parser.add_argument("--sleep", type=float, default=0.2, help="Pause par thread entre requêtes (s)")
    parser.add_argument("--timeout", type=float, default=30.0, help="Timeout HTTP (s)")
    parser.add_argument("--env", type=str, default=None,
                        help=".env à charger EN PRIORITÉ (ex. C:/dev/MulhouseGPT/.env.local pour la prod)")
    args = parser.parse_args()

    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    if args.env:
        load_dotenv(args.env, override=True)

    if not convex_client.use_convex():
        print("❌ Convex non configuré : définir CONVEX_DEPLOY_KEY et NEXT_PUBLIC_CONVEX_URL.")
        sys.exit(1)
    print(f"[*] Backend : Convex (cloud) — {convex_client.get_convex_url()}")

    print("[*] Liste des articles sans image…")
    candidates = list_candidates()
    print(f"[*] {len(candidates)} articles lalsace.fr sans image")

    from_index = args.from_index
    if args.reprendre:
        try:
            with open(CHECKPOINT_FILE, encoding="utf-8") as f:
                saved = json.load(f)
            if saved.get("deployment") == convex_client.get_convex_url():
                from_index = max(from_index, int(saved.get("done", 0)))
                print(f"[*] Checkpoint trouvé : reprise à {from_index}")
            else:
                print("[*] Checkpoint d'un autre déploiement — ignoré.")
        except (OSError, ValueError):
            print("[*] Aucun checkpoint exploitable.")
    if from_index > 0:
        candidates = candidates[from_index:]
        print(f"[*] {len(candidates)} restants après saut des {from_index} premiers")
    if args.limit:
        candidates = candidates[:args.limit]
        print(f"[*] Plafonné à {len(candidates)} (--limit)")
    total = len(candidates)

    done = fixed = updated = no_og = hors_cdn = network_err = 0
    consecutive_failures = 0
    lock = threading.Lock()
    start_time = datetime.now()

    def save_checkpoint() -> None:
        try:
            with open(CHECKPOINT_FILE, "w", encoding="utf-8") as f:
                json.dump({"done": from_index + done, "total": from_index + total,
                           "deployment": convex_client.get_convex_url(),
                           "savedAt": datetime.now().isoformat()}, f)
        except OSError:
            pass

    def progress() -> None:
        elapsed = (datetime.now() - start_time).total_seconds()
        rate = done / elapsed if elapsed > 0 else 0.0
        remaining = (total - done) / rate if rate > 0 else float("inf")
        print(
            f"   [{done}/{total}] photos trouvées: {fixed} (écrites: {updated}) "
            f"| sans og:image: {no_og} | hors CDN: {hors_cdn} | erreurs réseau: {network_err} "
            f"| débit {rate:.1f}/s | ETA {fmt_eta(remaining)}"
        )

    def process(link: str) -> str:
        nonlocal consecutive_failures, no_og, hors_cdn, network_err
        img, err = fetch_og_image(link, args.timeout)
        time.sleep(args.sleep + random.uniform(0, 0.2))
        if not img:
            with lock:
                if err and "réseau" in err:
                    network_err += 1
                    consecutive_failures += 1
                elif err and "hors CDN" in err:
                    hors_cdn += 1
                    consecutive_failures = 0
                else:
                    no_og += 1
                    consecutive_failures = 0
            return "echec"
        with lock:
            consecutive_failures = 0
        print(f"    [+] {img[:90]}")
        if not args.dry_run:
            convex_client.upsert_article({
                "link": link,
                "imageUrl": img,
                "updatedAt": int(time.time() * 1000),
            })
        return "ok"

    with ThreadPoolExecutor(max_workers=max(1, args.workers)) as pool:
        futures = {pool.submit(process, link): link for link in candidates}
        for future in as_completed(futures):
            done += 1
            try:
                status = future.result()
            except Exception as exc:  # noqa: BLE001
                status = "erreur"
                print(f"    [!] {futures[future]}: {exc}")
            with lock:
                if status == "ok":
                    fixed += 1
                    if not args.dry_run:
                        updated += 1
            if done % 25 == 0:
                progress()
                save_checkpoint()
            if consecutive_failures >= MAX_CONSECUTIVE_NETWORK_FAILURES:
                print(f"[!] {consecutive_failures} échecs réseau consécutifs — arrêt.")
                pool.shutdown(wait=False, cancel_futures=True)
                break

    progress()
    save_checkpoint()
    label = "photos trouvées (dry-run)" if args.dry_run else "images écrites dans Convex"
    print(f"\n[*] TERMINÉ : {fixed} {label}, {no_og} sans og:image, "
          f"{hors_cdn} hors CDN, {network_err} erreurs réseau.")


if __name__ == "__main__":
    main()
