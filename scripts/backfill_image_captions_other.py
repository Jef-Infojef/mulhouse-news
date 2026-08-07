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
    sans_legende = 0
    fetch_errors = 0

    for i, (art_id, link, image_url) in enumerate(rows, 1):
        result = fetch_page_caption(link, {}, False, image_url)
        short_link = link if len(link) <= 70 else link[:67] + "…"

        if result.caption:
            cur.execute(
                'UPDATE "Article" SET "imageCaption" = %s WHERE id = %s',
                (result.caption, art_id),
            )
            conn.commit()
            ok += 1
            print(f"[{i}/{total} | ok:{ok} sans:{sans_legende} err:{fetch_errors}] SUCCÈS | {short_link}")
            print(f"         → {result.caption[:90]}{'…' if len(result.caption) > 90 else ''}")

        elif result.fetched:
            cur.execute(
                'UPDATE "Article" SET "imageCaption" = %s WHERE id = %s',
                (NO_CAPTION, art_id),
            )
            conn.commit()
            sans_legende += 1
            print(
                f"[{i}/{total} | ok:{ok} sans:{sans_legende} err:{fetch_errors}] "
                f"SANS LÉGENDE | {short_link}"
            )
            print("         → source sans légende (marqué, plus retenté)")

        else:
            fetch_errors += 1
            status_note = f"HTTP {result.status_code}" if result.status_code else "réseau/timeout"
            print(
                f"[{i}/{total} | ok:{ok} sans:{sans_legende} err:{fetch_errors}] "
                f"ÉCHEC CHARGEMENT | {short_link}"
            )
            print(f"         → {status_note} (imageCaption laissé NULL, retentable)")

        time.sleep(random.uniform(0.3, 0.8))

        if i % 25 == 0 or i == total:
            done = ok + sans_legende
            print(
                f"Progression : {i}/{total} | succès {ok} | sans légende {sans_legende} | "
                f"échecs chargement {fetch_errors} | reste ~{max(pending_total - done, 0)} en attente"
            )

    print("\n--- Résumé ---")
    print(f"Succès        : {ok}/{total}")
    print(f"Sans légende  : {sans_legende}/{total} (marqués, plus retentés)")
    print(f"Échec chargem.: {fetch_errors}/{total} (NULL, retentables)")
    print(f"Restant       : ~{max(pending_total - ok - sans_legende, 0)} article(s) jamais tentés")
    conn.close()


if __name__ == "__main__":
    main()