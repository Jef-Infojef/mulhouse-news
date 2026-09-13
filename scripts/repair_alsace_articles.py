"""Rattrapage des articles L'Alsace incomplets (source « (archive) », titre slug, photos et métadonnées).

Récupère l'ensemble des informations disponibles sur la page publique sans compte abonné :
  - Vrai titre accentué (og:title)
  - Description / chapô (og:description)
  - Image principale HD (og:image) et légende (figcaption / alt)
  - Galeries photos et diaporamas complets enregistrés dans `articleImages`
  - Auteur (dataLayer dimension61)
  - Rubrique / catégorie (dataLayer dimension15)
  - Date de publication exacte (dataLayer dimension22 / ISO)
  - Texte de l'article si absent (JSON-LD articleBody ou chapô + texte public)
  - Migration de source « L'Alsace (archive) » vers « L'Alsace »

Deux ordres de traitement :
  • `--order recent` (défaut) : les plus récents d'abord, ce que la home affiche.
  • `--order source` : balayage exhaustif par source pour le rattrapage de fond.

Usage :
    python scripts/repair_alsace_articles.py --dry-run --limit 20
    python scripts/repair_alsace_articles.py --limit 300
    python scripts/repair_alsace_articles.py --order source --only-legacy --limit 1000

Backend : Convex cloud (academic-spoonbill-914).
"""

from __future__ import annotations

import argparse
import json
import os
import random
import sys
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

from bs4 import BeautifulSoup
from curl_cffi import requests as curl_requests
from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import convex_client
from scrape_utils import extract_article_images, parse_ebra_page_meta

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
    """À réparer, du plus récent au plus ancien (scrapers:getArticlesToRepairPage)."""
    rows = convex_client.get_articles_to_repair(
        [SOURCE, SOURCE_LEGACY], SOURCE_LEGACY, max_articles=max_articles
    )
    out = [
        {
            "link": r["link"],
            "needs_source": r["needsSource"],
            "needs_image": r["needsImage"],
            "has_content": r.get("hasContent", False),
            "supabase_id": r.get("supabaseId"),
            "published_at": r.get("publishedAt"),
        }
        for r in rows
    ]
    legacy = sum(1 for r in out if r["needs_source"])
    print(
        f"[*] {len(out)} articles à réparer ({legacy} sous « {SOURCE_LEGACY} », "
        f"{len(out) - legacy} déjà sous « {SOURCE} » mais sans photo)"
    )
    return out


def list_candidates_by_source(only_legacy: bool, max_articles: int = 0) -> list[dict]:
    """Balayage exhaustif par source (index by_source), sans ordre de date."""
    rows: list[dict] = []
    for link in convex_client.get_article_links(
        source=SOURCE_LEGACY, max_links=max_articles or None
    ):
        rows.append(
            {
                "link": link,
                "needs_source": True,
                "needs_image": True,
                "has_content": False,
                "supabase_id": None,
            }
        )
    print(f"[*] {len(rows)} articles sous « {SOURCE_LEGACY} » à ramener sous « {SOURCE} »")

    if only_legacy or (max_articles and len(rows) >= max_articles):
        return rows[:max_articles] if max_articles else rows

    before = len(rows)
    remaining = (max_articles - len(rows)) if max_articles else None
    for art in convex_client.get_article_titles(source=SOURCE, max_articles=remaining):
        if art.get("imageUrl"):
            continue
        rows.append(
            {
                "link": art["link"],
                "needs_source": False,
                "needs_image": True,
                "has_content": False,
                "supabase_id": None,
            }
        )
    print(f"[*] {len(rows) - before} articles déjà sous « {SOURCE} » mais sans photo")
    return rows[:max_articles] if max_articles else rows


def fmt_eta(seconds: float) -> str:
    seconds = int(seconds)
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    return f"{h}h{m:02d}m{s:02d}s" if h else f"{m}m{s:02d}s"


def build_patch(candidate: dict, html: str) -> tuple[dict, list[dict]]:
    """Extrait l'ensemble des informations disponibles sur la page publique."""
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
        if meta.get(meta_key):
            patch[field] = meta[meta_key]

    # Date de publication exacte si disponible
    if meta.get("published_at_iso"):
        try:
            pub_dt = datetime.fromisoformat(meta["published_at_iso"].replace("Z", "+00:00"))
            patch["publishedAt"] = int(pub_dt.timestamp() * 1000)
        except Exception:
            pass

    soup = BeautifulSoup(html, "html.parser")

    # Contenu textuel si manquant dans le document
    if not candidate.get("has_content"):
        body_text = None
        # 1. Essai JSON-LD (dépêches, vidéos, articles ouverts)
        for script in soup.find_all("script", type="application/ld+json"):
            try:
                raw = script.string.strip()
                data = json.loads(raw)
                items = data.get("@graph", data) if isinstance(data, dict) else data
                if isinstance(items, dict):
                    items = [items]
                for item in items:
                    if isinstance(item, dict) and item.get("articleBody"):
                        b = item["articleBody"].strip()
                        if len(b) > 100:
                            body_text = b
                            break
            except Exception:
                pass
            if body_text:
                break

        # 2. Essai texte HTML (chapô + corps public)
        if not body_text:
            blocks = []
            chapo = soup.find(class_="chapo") or soup.find(class_="article__chapo")
            if chapo:
                t = chapo.get_text(" ", strip=True)
                if len(t) > 20:
                    blocks.append(t)
            for block in soup.find_all("div", class_="textComponent"):
                t = block.get_text("\n", strip=True)
                if len(t) > 20:
                    blocks.append(t)
            if not blocks:
                inner = soup.find(class_="innerContent")
                if inner:
                    t = inner.get_text("\n", strip=True)
                    if len(t) > 20:
                        blocks.append(t)
            if blocks:
                body_text = "\n\n".join(blocks)

        if body_text and len(body_text) >= 100:
            patch["content"] = body_text

    # Images complètes (hero + galeries / diaporamas)
    all_images = extract_article_images(
        soup,
        candidate["link"],
        image_url=patch.get("imageUrl"),
        image_caption=patch.get("imageCaption"),
    )

    return patch, all_images


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Rattrapage complet des articles L'Alsace (photos, galeries, métadonnées, auteur, etc.)"
    )
    parser.add_argument("--dry-run", action="store_true", help="Sonde et affiche sans écrire")
    parser.add_argument(
        "--limit", type=int, default=0, help="Plafonne le nombre d'articles traités (0 = illimité)"
    )
    parser.add_argument(
        "--only-legacy",
        action="store_true",
        help="Ne traiter que la migration de source « (archive) » → « L'Alsace »",
    )
    parser.add_argument(
        "--order",
        choices=["recent", "source"],
        default="recent",
        help="'recent' (défaut) : les plus récents d'abord, ce que voit la home. "
        "'source' : balayage exhaustif par source pour le rattrapage de fond.",
    )
    parser.add_argument("--workers", type=int, default=5, help="Threads parallèles (défaut 5)")
    parser.add_argument(
        "--sleep", type=float, default=0.2, help="Pause par thread entre deux requêtes (s)"
    )
    parser.add_argument(
        "--timeout", type=float, default=30.0, help="Timeout HTTP par requête (s)"
    )
    parser.add_argument(
        "--env",
        type=str,
        default=None,
        help="Fichier .env à charger EN PRIORITÉ (ex. celui du déploiement prod)",
    )
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
        candidates = list_candidates_by_source(args.only_legacy, max_articles=args.limit)

    if args.limit:
        candidates = candidates[: args.limit]
    total = len(candidates)
    print(f"[*] {total} articles à traiter")
    if not total:
        return

    done = migrated = with_image = no_image = gone = network_err = 0
    with_author = with_category = with_content = with_gallery = gallery_images_count = 0
    consecutive_failures = 0
    lock = threading.Lock()
    start_time = datetime.now()

    def progress() -> None:
        elapsed = (datetime.now() - start_time).total_seconds()
        rate = done / elapsed if elapsed > 0 else 0.0
        remaining = (total - done) / rate if rate > 0 else float("inf")
        pct = (done / total * 100.0) if total else 0.0
        print(
            f"   [{done}/{total} ({pct:.1f}%)] photo: {with_image} | galeries: {with_gallery} (+{gallery_images_count} imgs) "
            f"| auteur: {with_author} | texte: {with_content} | migrés: {migrated} "
            f"| débit {rate:.1f}/s | ETA {fmt_eta(remaining)}",
            flush=True,
        )

    def process(candidate: dict) -> None:
        nonlocal done, migrated, with_image, no_image, gone, network_err, consecutive_failures
        nonlocal with_author, with_category, with_content, with_gallery, gallery_images_count

        html, err = fetch_page(candidate["link"], args.timeout)
        time.sleep(args.sleep + random.uniform(0, 0.2))

        patch, all_images = build_patch(candidate, html) if html else (None, [])
        # Page injoignable : on migre quand même la source pour ne pas bloquer l'article
        if patch is None and candidate["needs_source"]:
            patch = {"link": candidate["link"], "source": SOURCE}

        num_images = len(all_images)
        has_hero = bool(patch and patch.get("imageUrl"))

        with lock:
            if html:
                consecutive_failures = 0
                if has_hero:
                    with_image += 1
                else:
                    no_image += 1
                if patch and patch.get("author"):
                    with_author += 1
                if patch and patch.get("category"):
                    with_category += 1
                if patch and patch.get("content"):
                    with_content += 1
                if num_images > 1:
                    with_gallery += 1
            elif err and err.startswith("HTTP 4"):
                consecutive_failures = 0
                gone += 1
            else:
                consecutive_failures += 1
                network_err += 1

        if patch and not args.dry_run:
            try:
                patch["updatedAt"] = int(time.time() * 1000)
                # Assurer un supabaseId pour lier les images
                if not candidate.get("supabase_id"):
                    patch["supabaseId"] = str(uuid.uuid4())

                res = convex_client.upsert_article(patch)
                supabase_id = (
                    (res.get("supabaseId") if res else None)
                    or patch.get("supabaseId")
                    or candidate.get("supabase_id")
                )

                # Sauvegarde des images dans articleImages
                if all_images and supabase_id:
                    rows = []
                    for pos, img in enumerate(all_images):
                        u = (img.get("url") or "").strip()
                        if not u:
                            continue
                        rows.append(
                            {
                                "articleId": supabase_id,
                                "url": u,
                                "caption": img.get("caption"),
                                "position": pos,
                                "source": img.get("source") or ("hero" if pos == 0 else "gallery"),
                            }
                        )
                    if rows:
                        convex_client.upsert_article_images(rows)
                        with lock:
                            gallery_images_count += len(rows)

                if candidate["needs_source"]:
                    with lock:
                        migrated += 1
            except convex_client.ConvexError as exc:
                print(f"    [!] Écriture refusée ({candidate['link']}): {str(exc)[:120]}")
        elif patch and args.dry_run:
            if candidate["needs_source"]:
                with lock:
                    migrated += 1
            if all_images:
                with lock:
                    gallery_images_count += len(all_images)

        with lock:
            done += 1
            if done % 25 == 0 or done == total:
                progress()

    with ThreadPoolExecutor(max_workers=max(1, args.workers)) as pool:
        futures = [pool.submit(process, c) for c in candidates]
        for future in as_completed(futures):
            future.result()
            if consecutive_failures >= MAX_CONSECUTIVE_NETWORK_FAILURES:
                print(
                    f"\n❌ {MAX_CONSECUTIVE_NETWORK_FAILURES} échecs réseau consécutifs — arrêt."
                )
                for pending in futures:
                    pending.cancel()
                break

    print(
        f"\n[*] {'SONDE' if args.dry_run else 'TERMINÉ'} : {done} traités, "
        f"{migrated} sources migrées sous « {SOURCE} », {with_image} avec photo principale, "
        f"{with_gallery} avec galerie multi-images ({gallery_images_count} photos au total), "
        f"{with_author} avec auteur, {with_content} avec texte récupéré, "
        f"{no_image} sans photo exploitable, {gone} pages disparues, {network_err} erreurs réseau."
    )


if __name__ == "__main__":
    main()
