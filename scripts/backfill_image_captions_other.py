"""Rattrapage des légendes photo pour les articles hors EBRA.

Cible les articles avec imageUrl mais sans imageCaption, excluant
lalsace.fr, dna.fr, estrepublicain.fr et vosgesmatin.fr (script dédié).

Usage (depuis la racine mulhouse-news) :
  npm run backfill:captions:other
  npm run backfill:captions:other -- --limit 50
  python scripts/backfill_image_captions_other.py --limit 50
"""
import argparse
import os
import re
import sys
import time
import random
import psycopg2
from collections import Counter
from dotenv import load_dotenv

_script_dir = os.path.dirname(os.path.abspath(__file__))
if _script_dir not in sys.path:
    sys.path.insert(0, _script_dir)

from scrape_utils import EBRA_DOMAINS, fetch_page_caption

_root = os.path.dirname(_script_dir)
for _env in (".envenv", ".env.local", ".env"):
    load_dotenv(os.path.join(_root, _env))

DATABASE_URL = os.environ.get("DATABASE_URL", "").replace("?pgbouncer=true", "").replace("&pgbouncer=true", "")

NO_CAPTION = ""
CONSECUTIVE_FAILURE_LIMIT = 10


def _ebra_exclude_clause() -> str:
    parts = " OR ".join(f"link LIKE '%%{d}%%'" for d in EBRA_DOMAINS)
    return f"NOT ({parts})"


def _domain(link: str) -> str:
    m = re.search(r"https?://([^/]+)", link or "")
    return m.group(1).lower() if m else "?"


def main():
    parser = argparse.ArgumentParser(description="Rattrapage légendes photo (hors EBRA)")
    parser.add_argument("--limit", type=int, default=int(os.environ.get("CAPTION_BACKFILL_OTHER_LIMIT", "30")))
    args = parser.parse_args()
    limit = args.limit

    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()

    where_clause = f"""
        "imageCaption" IS NULL
        AND "imageUrl" IS NOT NULL AND "imageUrl" <> ''
        AND {_ebra_exclude_clause()}
    """

    cur.execute(f'SELECT COUNT(*) FROM "Article" WHERE {where_clause}')
    pending_total = cur.fetchone()[0]

    cur.execute(
        f"""
        SELECT link FROM "Article"
        WHERE {where_clause}
        ORDER BY "publishedAt" DESC
        LIMIT 200
        """
    )
    sample_links = [r[0] for r in cur.fetchall()]
    top_domains = Counter(_domain(l) for l in sample_links).most_common(8)

    cur.execute(
        f"""
        SELECT id, link, "imageUrl" FROM "Article"
        WHERE {where_clause}
        ORDER BY "publishedAt" DESC
        LIMIT %s
        """,
        (limit,),
    )
    rows = cur.fetchall()
    total = len(rows)

    print("--- Rattrapage légendes photo (hors EBRA) ---")
    print(f"Articles à traiter : {total} (sur {pending_total} en attente)")
    if top_domains:
        print("Top domaines en attente :", ", ".join(f"{d} ({n})" for d, n in top_domains))
    print()

    ok = 0
    failed = 0
    consecutive_failures = 0
    pending_failures: list[str] = []
    stopped_early = False

    for i, (art_id, link, image_url) in enumerate(rows, 1):
        caption = fetch_page_caption(link, {}, False, image_url)
        short_link = link if len(link) <= 70 else link[:67] + "…"
        if caption:
            for pid in pending_failures:
                cur.execute(
                    'UPDATE "Article" SET "imageCaption" = %s WHERE id = %s',
                    (NO_CAPTION, pid),
                )
            if pending_failures:
                conn.commit()
                failed += len(pending_failures)
                pending_failures.clear()
            consecutive_failures = 0

            cur.execute(
                'UPDATE "Article" SET "imageCaption" = %s WHERE id = %s',
                (caption, art_id),
            )
            conn.commit()
            ok += 1
            print(f"[{i}/{total} | ok:{ok} échecs:{failed}] SUCCÈS | {short_link}")
            print(f"         → {caption[:90]}{'…' if len(caption) > 90 else ''}")
        else:
            consecutive_failures += 1
            pending_failures.append(art_id)

            if consecutive_failures >= CONSECUTIVE_FAILURE_LIMIT:
                stopped_early = True
                print(
                    f"\n⛔ Arrêt : {CONSECUTIVE_FAILURE_LIMIT} échecs consécutifs "
                    f"(probable blocage réseau ou rate-limit). "
                    f"{len(pending_failures)} article(s) non marqués."
                )
                break

            print(f"[{i}/{total} | ok:{ok} échecs:{failed + len(pending_failures)}] IGNORÉ | {short_link}")
            print("         → pas de légende (en attente de confirmation)")

        time.sleep(random.uniform(0.3, 0.8))

        if i % 25 == 0 or i == total:
            done = ok + failed + (0 if stopped_early else len(pending_failures))
            print(f"Progression : {i}/{total} | succès {ok} | ignorés {failed} | reste ~{max(pending_total - done, 0)} en attente")

    if pending_failures and not stopped_early:
        for pid in pending_failures:
            cur.execute(
                'UPDATE "Article" SET "imageCaption" = %s WHERE id = %s',
                (NO_CAPTION, pid),
            )
        conn.commit()
        failed += len(pending_failures)
        pending_failures.clear()

    print("\n--- Résumé ---")
    if stopped_early:
        print(f"Succès   : {ok} (arrêt anticipé après {CONSECUTIVE_FAILURE_LIMIT} échecs consécutifs)")
        print(f"Ignorés  : {failed} (marqués avant blocage)")
        print(f"Non marqués : {len(pending_failures)} (imageCaption NULL, retentables plus tard)")
    else:
        print(f"Succès   : {ok}/{total}")
        print(f"Ignorés  : {failed}/{total} (marqués, plus retentés)")
    print(f"Restant  : ~{max(pending_total - ok - failed, 0)} article(s) jamais tentés")
    conn.close()


if __name__ == "__main__":
    main()