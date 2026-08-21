"""Migration ciblée des articles L'Alsace de Supabase → Convex.

Lit tous les articles lalsace.fr depuis Supabase (DATABASE_URL) et les upsert
dans Convex (CONVEX_DEPLOY_KEY + NEXT_PUBLIC_CONVEX_URL) via
`convex_client.upsert_article`. La déduplication par lien est gérée côté
Convex (upsert), donc relancer est sûr (idempotent).

Usage :
    USE_CONVEX=1 python scripts/migrate_alsace_supabase_to_convex.py
    USE_CONVEX=1 python scripts/migrate_alsace_supabase_to_convex.py --source "L'Alsace (archive)"
"""

import argparse
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

import psycopg2
from dotenv import load_dotenv

import convex_client

load_dotenv(".env.local")
load_dotenv(".env")

SOURCE_LIKE = "%lalsace.fr%"


def get_pg():
    url = os.environ.get("DATABASE_URL", "").replace("?pgbouncer=true", "").replace("&pgbouncer=true", "")
    if not url:
        raise SystemExit("DATABASE_URL manquante")
    return psycopg2.connect(url)


def main():
    parser = argparse.ArgumentParser(description="Migre les articles L'Alsace de Supabase vers Convex")
    parser.add_argument("--limit", type=int, default=0, help="Nombre max d'articles (0 = tout)")
    args = parser.parse_args()

    if not convex_client.use_convex():
        raise SystemExit(
            "Backend Convex non configuré : définir CONVEX_DEPLOY_KEY et NEXT_PUBLIC_CONVEX_URL "
            "(ou USE_CONVEX=1)"
        )

    conn = get_pg()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT id, title, link, "imageUrl", "imageCaption", source, description,
               "publishedAt", content, "createdAt", "updatedAt", hidden
        FROM "Article"
        WHERE link LIKE %s
        ORDER BY "publishedAt" ASC
        LIMIT %s
        """,
        (SOURCE_LIKE, args.limit or 1_000_000_000),
    )
    rows = cur.fetchall()
    cur.close()
    conn.close()
    print(f"[*] {len(rows)} articles L'Alsace lus depuis Supabase.")

    def ms(v):
        if v is None:
            return None
        if isinstance(v, datetime):
            return int(v.timestamp() * 1000)
        return int(v)

    def clean(v):
        return None if v is None else v

    def to_row(r):
        return {
            "supabaseId": r[0],
            "title": r[1],
            "link": r[2],
            "imageUrl": clean(r[3]),
            "imageCaption": clean(r[4]),
            "source": clean(r[5]),
            "description": clean(r[6]),
            "publishedAt": ms(r[7]),
            "content": clean(r[8]),
            "createdAt": ms(r[9]),
            "updatedAt": ms(r[10]),
            "hidden": bool(r[11]),
        }

    # Upserts Convex en parallèle : chaque article = un appel HTTP séquentiel
    # (~0,6 s), la sérialisation en faisait ~1,5 article/s. Un pool de workers
    # envoie plusieurs mutations simultanément (Convex gère la concurrence).
    # On garde un nombre borné de requêtes en vol pour ne pas noyer l'API.
    workers = int(os.environ.get("MIGRATE_CONCURRENCY", "12"))
    inserted = updated = errors = 0
    start = time.time()
    done = 0
    with ThreadPoolExecutor(max_workers=workers) as pool:
        in_flight: dict = {}
        row_iter = iter(rows)
        def submit_next():
            r = next(row_iter, None)
            if r is None:
                return False
            in_flight[pool.submit(convex_client.upsert_article, to_row(r))] = r[2]
            return True
        for _ in range(workers):
            submit_next()
        while in_flight:
            fut = next(as_completed(in_flight))
            link = in_flight.pop(fut)
            try:
                res = fut.result()
                if res and res.get("created"):
                    inserted += 1
                else:
                    updated += 1
            except Exception as e:
                errors += 1
                if errors <= 5:
                    print(f"    [!] Échec ({link}): {e}")
            done += 1
            submit_next()
            if done % 500 == 0:
                el = time.time() - start
                rate = done / el if el else 0
                print(f"    [{done}/{len(rows)}] +{inserted} insérés, {updated} à jour, {errors} erreurs ({el:.0f}s, {rate:.1f}/s)")

    print(f"\n[*] TERMINÉ : {len(rows)} lus | +{inserted} insérés | {updated} déjà présents/mis à jour | {errors} erreurs")


if __name__ == "__main__":
    main()