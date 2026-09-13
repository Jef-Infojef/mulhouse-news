"""Récupère dans Supabase les `imageUrl` perdues lors de la migration vers Convex.

La migration Supabase → Convex a laissé des articles sans `imageUrl` alors que
l'ancienne base en avait une. En croisant par `link`, ces photos se récupèrent
par jointure, sans ouvrir une seule page de lalsace.fr — là où
`repair_alsace_articles.py` doit faire une requête HTTP par article.

Mesure du 11/09/2026 : 42 706 articles sans photo côté Convex, 19 508
correspondances dans Supabase, dont **6 877 exploitables**.

Les 12 631 autres pointent toutes vers la même image — la une de « L'Alsace —
Édition du soir » (`013e8394-870a-4784-be52-5e1e981da78b`), recopiée sur des
brèves sans illustration propre (pharmacies de garde, résultats de clubs, noms
de rues). Elles sont écartées : les importer poserait la même vignette de
journal sur 12 631 cartes, que le filtre anti-doublon d'`app/actions.ts`
écarterait ensuite de la home. Vérification faite, ces articles n'ont pas
davantage de photo sur le site aujourd'hui (0 sur 8 sondés).

Usage :
    python scripts/restore_images_from_supabase.py --dry-run      # sonde
    python scripts/restore_images_from_supabase.py                # run complet
    python scripts/restore_images_from_supabase.py --limit 500    # plafonner
    python scripts/restore_images_from_supabase.py --check-urls   # valider en HTTP d'abord

Supabase est gelée depuis le 23/08/2026 : ses URL de CDN pourraient avoir
expiré. Un échantillon de 120 répondait 200 sur 120 ; `--check-urls` permet de
revérifier avant d'écrire si le doute revient.

Sources : Supabase via DATABASE_URL (lecture seule), Convex via
CONVEX_DEPLOY_KEY + NEXT_PUBLIC_CONVEX_URL (écriture).
"""

from __future__ import annotations

import argparse
import os
import random
import sys
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor

import psycopg2
from curl_cffi import requests as curl_requests
from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import convex_client

load_dotenv(".env.local")
load_dotenv()

# Une de « L'Alsace — Édition du soir », servie par défaut aux brèves sans photo.
PLACEHOLDER_FRAGMENT = "013e8394-870a-4784-be52-5e1e981da78b"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"


def convex_links_sans_photo() -> list[str]:
    """Liens des articles Convex sans `imageUrl` (index by_imageUrl, paginé)."""
    liens: list[str] = []
    cursor: str | None = None
    while True:
        res = convex_client._call(
            "stats:countMissingPhotoLinksPage",
            {"cursor": cursor, "limit": 500},
            mutation=False,
        )
        liens.extend(res["links"])
        if res["isDone"]:
            break
        cursor = res["continueCursor"]
    return liens


def supabase_images() -> dict[str, tuple[str, str | None]]:
    """{link: (imageUrl, imageCaption)} des articles Supabase illustrés."""
    url = (
        os.environ["DATABASE_URL"]
        .replace("?pgbouncer=true", "")
        .replace("&pgbouncer=true", "")
    )
    conn = psycopg2.connect(url)
    try:
        with conn.cursor() as cur:
            cur.execute(
                'SELECT link, "imageUrl", "imageCaption" FROM "Article" '
                "WHERE \"imageUrl\" IS NOT NULL AND \"imageUrl\" <> ''"
            )
            return {link: (img, cap) for link, img, cap in cur.fetchall()}
    finally:
        conn.close()


def url_repond(image_url: str, timeout: float = 20.0) -> bool:
    """HEAD sur l'image (repli GET si la méthode est refusée)."""
    try:
        resp = curl_requests.head(
            image_url, timeout=timeout, impersonate="chrome110", headers={"User-Agent": UA}
        )
        if resp.status_code == 405:
            resp = curl_requests.get(
                image_url, timeout=timeout, impersonate="chrome110", headers={"User-Agent": UA}
            )
        return resp.status_code == 200
    except Exception:  # noqa: BLE001 — erreur réseau
        return False


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Récupère les imageUrl perdues à la migration, depuis Supabase"
    )
    parser.add_argument("--dry-run", action="store_true", help="Sonde et affiche sans écrire")
    parser.add_argument("--limit", type=int, default=0, help="Plafonne le nombre d'articles (0 = tout)")
    parser.add_argument("--check-urls", action="store_true",
                        help="Vérifie en HTTP que chaque image répond avant de l'écrire")
    parser.add_argument("--workers", type=int, default=8, help="Threads pour --check-urls (défaut 8)")
    parser.add_argument("--env", type=str, default=None,
                        help="Fichier .env à charger EN PRIORITÉ")
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
    if not os.environ.get("DATABASE_URL"):
        print("❌ DATABASE_URL (Supabase) non définie : rien à croiser.")
        sys.exit(1)
    print(f"[*] Convex : {convex_client.get_convex_url()}")

    print("[*] Lecture des articles Convex sans photo…")
    manquants = convex_links_sans_photo()
    print(f"    {len(manquants)} articles sans imageUrl")

    print("[*] Lecture des articles illustrés de Supabase…")
    supabase = supabase_images()
    print(f"    {len(supabase)} articles avec imageUrl")

    correspondances = {lien: supabase[lien] for lien in manquants if lien in supabase}
    retenus = {
        lien: valeur
        for lien, valeur in correspondances.items()
        if PLACEHOLDER_FRAGMENT not in valeur[0]
    }
    ecartes = len(correspondances) - len(retenus)
    distinctes = len({v[0] for v in retenus.values()})
    print(
        f"\n[*] {len(correspondances)} correspondances — "
        f"{ecartes} écartées (une « Édition du soir »), {len(retenus)} retenues "
        f"sur {distinctes} URL distinctes"
    )
    if not retenus:
        print("[*] Rien à récupérer.")
        return

    travail = list(retenus.items())
    if args.limit:
        travail = travail[: args.limit]
        print(f"[*] Plafonné à {len(travail)} (--limit)")

    if args.check_urls:
        print(f"[*] Vérification HTTP de {len(travail)} images…")
        with ThreadPoolExecutor(max_workers=max(1, args.workers)) as pool:
            ok = list(pool.map(lambda item: url_repond(item[1][0]), travail))
        avant = len(travail)
        travail = [item for item, valide in zip(travail, ok) if valide]
        print(f"    {len(travail)}/{avant} images répondent (HTTP 200)")
        if not travail:
            print("[*] Aucune image valide — rien n'est écrit.")
            return
    else:
        # Sondage bon marché : 60 URL tirées au hasard, pour repérer une
        # expiration massive du CDN sans payer une vérification complète.
        echantillon = random.sample([v[0] for _, v in travail], min(60, len(travail)))
        with ThreadPoolExecutor(max_workers=max(1, args.workers)) as pool:
            codes = Counter(pool.map(url_repond, echantillon))
        valides = codes.get(True, 0)
        print(f"[*] Sondage : {valides}/{len(echantillon)} images répondent")
        if valides < len(echantillon) * 0.9:
            print("    ⚠️ Taux anormalement bas — relancer avec --check-urls pour filtrer une à une.")
            if not args.dry_run:
                print("    Écriture annulée par précaution.")
                return

    if args.dry_run:
        print(f"\n[*] SONDE : {len(travail)} articles seraient mis à jour. Exemples :")
        for lien, (img, cap) in travail[:5]:
            print(f"    {lien[-62:]}")
            print(f"      → {img[:78]}")
            if cap:
                print(f"      légende : {cap[:66]}")
        return

    print(f"\n[*] Écriture de {len(travail)} images dans Convex…")
    ecrits = erreurs = avec_legende = 0
    debut = time.time()
    for index, (lien, (img, cap)) in enumerate(travail, 1):
        patch: dict = {"link": lien, "imageUrl": img, "updatedAt": int(time.time() * 1000)}
        if cap:
            patch["imageCaption"] = cap
        try:
            convex_client.upsert_article(patch)
            ecrits += 1
            if cap:
                avec_legende += 1
        except convex_client.ConvexError as exc:
            erreurs += 1
            print(f"    [!] Échec ({lien[-50:]}) : {str(exc)[:110]}")
        if index % 250 == 0 or index == len(travail):
            ecoule = time.time() - debut
            debit = index / ecoule if ecoule else 0
            print(f"    [{index}/{len(travail)}] écrits: {ecrits} | erreurs: {erreurs} | {debit:.0f}/s")

    print(
        f"\n[*] TERMINÉ : {ecrits} images restaurées "
        f"({avec_legende} avec légende), {erreurs} erreurs."
    )
    print("[*] Le reste des articles sans photo relève de repair_alsace_articles.py (scraping).")


if __name__ == "__main__":
    main()
