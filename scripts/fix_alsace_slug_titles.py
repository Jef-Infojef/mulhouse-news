"""Correction des titres L'Alsace dérivés du slug (sans accents, tout bas-de-casse).

`scrape_alsace_archive.py` insère les articles d'archive avec un titre dérivé
du slug d'URL (`title_from_slug`) car les sitemaps ne fournissent pas de titre :
« Mulhouse j y crois defend ses » au lieu de « Mulhouse j'y crois défend ses… ».
Ces titres remontent tels quels dans le RAG de MulhouseGPT (citations, réponses).

Ce script :
  1. liste (link, title) en quelques paginations légères Convex (sans content) ;
  2. filtre localement les titres slugifiés (aucune majuscule après la 1re
     lettre, aucun caractère accentué) — zéro requête par article ;
  3. en pool de threads, récupère la page lalsace.fr et lit `og:title` ;
  4. ne met à jour QUE si la normalisation de og:title correspond exactement
     à celle du slug (preuve que c'est bien le même article) ;
  5. met à jour le titre via `scrapers:upsertArticle` (patch par link).

Usage :
    python scripts/fix_alsace_slug_titles.py                    # run complet
    python scripts/fix_alsace_slug_titles.py --dry-run          # sonde sans écrire
    python scripts/fix_alsace_slug_titles.py --limit 200        # plafonner
    python scripts/fix_alsace_slug_titles.py --reprendre        # reprise checkpoint
    python scripts/fix_alsace_slug_titles.py --from 3550        # saut manuel
    python scripts/fix_alsace_slug_titles.py --workers 8        # plus de parallélisme

Backend : Convex uniquement (CONVEX_DEPLOY_KEY + NEXT_PUBLIC_CONVEX_URL requis,
et la query `scrapers:getArticleTitlesPage` déployée — repli sur lectures
unitaires sinon). Le script affiche sa progression (compteur, débit, ETA) et
s'arrête seul : fin de liste, limite atteinte, ou 30 échecs réseau consécutifs.
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
import unicodedata
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

from curl_cffi import requests as curl_requests
from dotenv import load_dotenv

import convex_client

# .env.local d'abord (clés Convex en local), .env en complément
load_dotenv(".env.local")
load_dotenv()

SOURCE_ARCHIVE = "L'Alsace (archive)"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"
CHECKPOINT_FILE = ".fix_alsace_titles_progress.json"

# Lettres accentuées/françaises absentes d'un slug ASCII : leur présence dans un
# titre prouve qu'il ne vient PAS du slug.
ACCENTED = set("àâäçéèêëîïôöùûüÿœæÀÂÄÇÉÈÊËÎÏÔÖÙÛÜŒÆ")

OG_TITLE_RES = [
    re.compile(r'<meta[^>]+property=["\']og:title["\'][^>]+content=["\'](.*?)["\']', re.I | re.S),
    re.compile(r'<meta[^>]+content=["\'](.*?)["\'][^>]+property=["\']og:title["\']', re.I | re.S),
]

MAX_CONSECUTIVE_NETWORK_FAILURES = 30


def looks_slug_derived(title: str | None) -> bool:
    """Titre candidat : aucune majuscule après la 1re lettre, aucun accent."""
    if not title or title == "Sans titre":
        return False
    if any(c in ACCENTED for c in title):
        return False
    return not any(c.isupper() for c in title[1:])


def norm_key(s: str) -> str:
    """Normalisation forte : bas-de-casse, sans accents, alphanumérique seul."""
    s = unicodedata.normalize("NFKD", s.lower())
    s = "".join(c for c in s if not unicodedata.combining(c))
    # œ/æ ne se décomposent pas en NFKD : remplacés manuellement
    s = s.replace("œ", "oe").replace("æ", "ae")
    return re.sub(r"[^a-z0-9]", "", s)


def slug_from_link(link: str) -> str:
    return link.rstrip("/").split("/")[-1]


def clean_slug(slug: str) -> str:
    """Retire les identifiants techniques en fin de slug : UUID (M+, avec ou
    sans tiret initial), numéro d'item ('-123', '_456_A' des agendas), qui
    n'existent pas dans le titre."""
    s = re.sub(r"-?[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}$", "", slug)
    s = re.sub(r"[-_]\d+[_A-Za-z]*$", "", s)
    return s


def titres_compatibles(og_norm: str, attendu_core: str) -> bool:
    """Égalité stricte, ou og:title PLUS RICHE que le slug (≥ 15 caractères) :
    certains sites complètent le titre (« Rendez-vous aux jardins - Mulhouse
    Musée… » pour un slug « rendez-vous-aux-jardins-1554961_A »). Le sens
    inverse est refusé : un og:title tronqué ne doit jamais passer."""
    if og_norm == attendu_core:
        return True
    return len(attendu_core) >= 15 and og_norm.startswith(attendu_core)


def title_variants(og: str) -> list[str]:
    """Variantes acceptées d'un og:title : brut, sans préfixe de rubrique
    (« Interactif. Mulhouse : … »), et sans suffixe de site (« | M+ »,
    « - ICI Alsace », « | L'Alsace »…). La normalisation (norm_key) fait le
    reste : la comparaison au slug reste stricte sur le fond."""
    hors_prefixe = og.split(". ", 1)[1] if ". " in og else None
    def couper_suffixes(s: str) -> str:
        s = s.split("|", 1)[0]
        s = re.split(r"\s+[-–—]\s+(?:ICI|L'Alsace|France Bleu|France 3)\b.*$", s)[0]
        return s.strip()
    variantes = {og.strip(), couper_suffixes(og)}
    if hors_prefixe:
        variantes.add(hors_prefixe)
        variantes.add(couper_suffixes(hors_prefixe))
    return [v for v in variantes if v]


def fetch_og_title(link: str, timeout: float) -> tuple[str | None, str | None]:
    """Retourne (og_title, erreur). og_title=None si page injoignable/absente."""
    err = "inconnue"
    for attempt in range(3):
        try:
            resp = curl_requests.get(
                link, timeout=timeout, impersonate="chrome110", headers={"User-Agent": UA}
            )
            if resp.status_code == 200:
                m = next((m for m in (r.search(resp.text) for r in OG_TITLE_RES) if m), None)
                if not m:
                    return None, "og:title absent"
                title = html.unescape(m.group(1)).strip()
                return (title or None), None if title else "og:title vide"
            if resp.status_code in (404, 410):
                return None, f"HTTP {resp.status_code} (article supprimé)"
            return None, f"HTTP {resp.status_code}"
        except Exception as exc:  # noqa: BLE001 — erreur réseau transitoire
            err = f"réseau: {exc}"
            time.sleep(1.5 * (attempt + 1))
    return None, err


def list_rows_fast(source: str) -> list[dict] | None:
    """Liste {link, title} sans content. Essaie la query légère
    scrapers:getArticleTitlesPage, puis repli sur news_bridge:getArticlesPage
    (content inclus mais présent sur tous les déploiements). None si aucun."""
    try:
        return convex_client.get_article_titles(source=source)
    except convex_client.ConvexError as exc:
        print(f"[!] Query légère indisponible ({str(exc)[:120]}…)")
    rows: list[dict] = []
    cursor: str | None = None
    while True:
        res = convex_client._call(
            "news_bridge:getArticlesPage",
            {"cursor": cursor, "limit": 200},
            mutation=False,
        )
        for a in res["articles"]:
            if a.get("link"):
                rows.append({"link": a["link"], "title": a.get("title") or ""})
        cursor = res.get("cursor")
        if res.get("isDone") or not cursor:
            break
    return rows


def list_rows_slow(source: str) -> list[dict]:
    """Repli : links paginées puis lecture unitaire du titre (lent)."""
    rows = []
    for i, link in enumerate(convex_client.get_article_links(source=source), 1):
        try:
            doc = convex_client.get_article_by_link(link)
        except convex_client.ConvexError as exc:
            print(f"    [!] Convex illisible ({link}): {exc}")
            doc = None
        rows.append({"link": link, "title": (doc or {}).get("title") or ""})
        if i % 500 == 0:
            print(f"    … {i} titres lus")
    return rows


def fmt_eta(seconds: float) -> str:
    seconds = int(seconds)
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    return f"{h}h{m:02d}m{s:02d}s" if h else f"{m}m{s:02d}s"


def main() -> None:
    parser = argparse.ArgumentParser(description="Correction des titres L'Alsace slugifiés")
    parser.add_argument("--dry-run", action="store_true", help="Sonde et affiche sans mettre à jour")
    parser.add_argument("--limit", type=int, default=0, help="Plafonne le nombre d'articles traités (0 = illimité)")
    parser.add_argument("--from", type=int, default=0, dest="from_index",
                        help="Ignore les N premiers candidats de la liste (reprise)")
    parser.add_argument("--reprendre", action="store_true",
                        help="Reprend depuis le checkpoint du run précédent (fichier de progression)")
    parser.add_argument("--workers", type=int, default=5, help="Threads parallèles (défaut 5)")
    parser.add_argument("--sleep", type=float, default=0.2, help="Pause par thread entre deux requêtes HTTP (s)")
    parser.add_argument("--timeout", type=float, default=30.0, help="Timeout HTTP par requête (s)")
    parser.add_argument("--env", type=str, default=None,
                        help="Fichier .env à charger EN PRIORITÉ (ex. --env C:/dev/MulhouseGPT/.env.local "
                             "pour viser le déploiement prod lu par le RAG)")
    args = parser.parse_args()

    if args.env:
        load_dotenv(args.env, override=True)

    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:  # noqa: BLE001
        pass

    if not convex_client.use_convex():
        print("❌ Convex non configuré : définir CONVEX_DEPLOY_KEY et NEXT_PUBLIC_CONVEX_URL (.env).")
        sys.exit(1)
    print(f"[*] Backend : Convex (cloud) — {convex_client.get_convex_url()}")

    print(f"[*] Liste des titres {SOURCE_ARCHIVE}…")
    rows = list_rows_fast(SOURCE_ARCHIVE)
    if rows is None:
        print("[*] Repli sur les lectures unitaires (déployer scrapers:getArticleTitlesPage pour accélérer)…")
        rows = list_rows_slow(SOURCE_ARCHIVE)
    print(f"[*] {len(rows)} articles d'archive")

    candidates = [r for r in rows if looks_slug_derived(r.get("title"))]
    print(f"[*] {len(candidates)} titres slugifiés à corriger "
          f"({len(rows) - len(candidates)} déjà corrects, sautés sans requête)")

    # Reprise : --from explicite, sinon checkpoint du run précédent (--reprendre).
    # Le checkpoint est lié au déploiement : un checkpoint d'un autre backend est ignoré.
    from_index = args.from_index
    if args.reprendre:
        try:
            with open(CHECKPOINT_FILE, encoding="utf-8") as f:
                saved = json.load(f)
            if saved.get("deployment") != convex_client.get_convex_url():
                print("[*] Checkpoint d'un autre déploiement — ignoré.")
            else:
                from_index = max(from_index, int(saved.get("done", 0)))
                print(f"[*] Checkpoint trouvé : reprise au candidat {from_index}")
        except (OSError, ValueError):
            print("[*] Aucun checkpoint exploitable — départ du début.")
    if from_index > 0:
        candidates = candidates[from_index:]
        print(f"[*] {len(candidates)} candidats restants après saut des {from_index} premiers")
    if args.limit:
        candidates = candidates[:args.limit]
        print(f"[*] Plafonné à {len(candidates)} candidats (--limit)")
    total = len(candidates)

    done = fixed = updated = already_ok = no_og = mismatch = network_err = 0
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
            f"   [{done}/{total}] corrigés: {fixed} (écrits: {updated}) | déjà corrects: {already_ok} "
            f"| sans og:title: {no_og} | hors sujet: {mismatch} | erreurs réseau: {network_err} "
            f"| débit {rate:.1f}/s | ETA {fmt_eta(remaining)}"
        )

    def process(row: dict) -> str:
        """Traite un candidat : fetch og:title, vérifie, met à jour. Renvoie un statut."""
        nonlocal consecutive_failures, no_og, network_err, mismatch
        link, current_title = row["link"], row.get("title") or ""
        # Slugs doublonnés ("-1") et identifiants techniques (UUID M+, ids
        # d'agenda) en suffixe : retirés avant comparaison.
        slug = clean_slug(slug_from_link(link))
        expected = norm_key(slug)
        expected_core = re.sub(r"\d+$", "", expected)
        if len(expected_core) < 8:
            # Slug purement technique (UUID nu, etc.) : aucune vérification
            # fiable possible, on ne touche pas.
            return "deja_ok"
        og_title, err = fetch_og_title(link, args.timeout)
        time.sleep(args.sleep + random.uniform(0, 0.2))
        if not og_title:
            if err and "réseau" in err:
                network_err += 1
                consecutive_failures += 1
            else:
                no_og += 1
                consecutive_failures = 0
            return "reseau" if (err and "réseau" in err) else "sans_og"
        consecutive_failures = 0
        # og:title EBRA/associés : préfixe de rubrique (« Interactif. Mulhouse :
        # … ») et suffixe de site (« | M+ », « - ICI Alsace ») à ignorer pour la
        # comparaison — et retirés du titre final.
        variantes = title_variants(og_title)
        # Égalité stricte d'abord (variante la plus propre = la plus courte) ;
        # sinon og:title enrichi accepté via préfixe.
        exactes = sorted((v for v in variantes if norm_key(v) == expected_core), key=len)
        garde = exactes[0] if exactes else next(
            (v for v in variantes if titres_compatibles(norm_key(v), expected_core)), None
        )
        if not garde:
            mismatch += 1
            if mismatch <= 20:
                print(f"    [?] hors sujet ({slug[:40]}) : {og_title[:70]}")
            return "hors_sujet"
        # Titre final : préfixe/suffixes retirés.
        nouveau = garde
        if nouveau == current_title:
            return "deja_ok"
        print(f"    [+] {current_title[:55]}\n        → {nouveau[:70]}")
        if not args.dry_run:
            convex_client.upsert_article({
                "link": link,
                "title": nouveau,
                "updatedAt": int(time.time() * 1000),
            })
        return "corrige"

    with ThreadPoolExecutor(max_workers=max(1, args.workers)) as pool:
        futures = {pool.submit(process, row): row for row in candidates}
        for future in as_completed(futures):
            done += 1
            try:
                status = future.result()
            except Exception as exc:  # noqa: BLE001 — mutation Convex ou imprévu
                status = "erreur"
                print(f"    [!] {futures[future]['link']}: {exc}")
            with lock:
                if status == "corrige":
                    fixed += 1
                    if not args.dry_run:
                        updated += 1
                elif status == "deja_ok":
                    already_ok += 1
                elif status == "sans_og":
                    no_og += 0  # déjà compté dans process()
                elif status == "reseau":
                    pass  # déjà compté dans process()
            if done % 25 == 0:
                progress()
                save_checkpoint()
            if consecutive_failures >= MAX_CONSECUTIVE_NETWORK_FAILURES:
                print(f"[!] {consecutive_failures} échecs réseau consécutifs — arrêt.")
                pool.shutdown(wait=False, cancel_futures=True)
                break

    progress()
    save_checkpoint()
    label = "titres corrigés (dry-run)" if args.dry_run else "titres mis à jour dans Convex"
    print(f"\n[*] TERMINÉ : {fixed} {label}, {already_ok} déjà corrects, "
          f"{no_og} sans og:title, {mismatch} og:title ≠ slug, {network_err} erreurs réseau.")


if __name__ == "__main__":
    main()
