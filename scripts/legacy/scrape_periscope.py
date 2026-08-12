"""Rattrapage / enrichissement du contenu Le Périscope (texte + images + légendes)."""
import argparse
import os

import psycopg2
from dotenv import load_dotenv

from scrape_utils import fetch_periscope_page, parse_periscope_article

load_dotenv(".env.local")
load_dotenv(".env")
DATABASE_URL = os.environ.get("DATABASE_URL")


def get_db_connection():
    clean_url = DATABASE_URL.replace("?pgbouncer=true", "").replace("&pgbouncer=true", "")
    return psycopg2.connect(clean_url)


def main():
    parser = argparse.ArgumentParser(description="Enrichir les articles Le Périscope")
    parser.add_argument(
        "--mode",
        choices=["missing", "enrich"],
        default="enrich",
        help="missing: sans contenu | enrich: sans <img> dans le contenu",
    )
    parser.add_argument("--limit", type=int, default=0, help="Nombre max d'articles")
    args = parser.parse_args()
    limit = args.limit if args.limit > 0 else None

    print("[*] Démarrage enrichissement Le Périscope...")
    conn = get_db_connection()
    cur = conn.cursor()

    if args.mode == "missing":
        where = """
            link LIKE '%%le-periscope.info%%'
            AND (content IS NULL OR LENGTH(content) < 100)
        """
    else:
        where = """
            link LIKE '%%le-periscope.info%%'
            AND (content IS NULL OR content NOT LIKE '%%<img%%')
        """

    cur.execute(f'SELECT COUNT(*) FROM "Article" WHERE {where}')
    pending = cur.fetchone()[0]

    query = f"""
        SELECT id, title, link
        FROM "Article"
        WHERE {where}
        ORDER BY "publishedAt" DESC NULLS LAST
    """
    if limit:
        query += f" LIMIT {limit}"
    cur.execute(query)
    articles = cur.fetchall()

    if not articles:
        print("Aucun article à traiter.")
        return

    print(f"[*] {len(articles)} articles à traiter (sur {pending} en attente).")

    success = 0
    for i, (art_id, title, link) in enumerate(articles, 1):
        if i % 25 == 0 or i == 1:
            print(f"[{i}/{len(articles)}] {title[:60]}...")

        soup = fetch_periscope_page(link)
        if not soup:
            print(f"   ⚠️ Page inaccessible: {link}")
            continue

        parsed = parse_periscope_article(soup, link)
        content = parsed.get("content")
        if not content or len(content) < 100:
            print(f"   ⚠️ Contenu insuffisant: {title[:50]}")
            continue

        try:
            cur.execute(
                """
                UPDATE "Article"
                SET content = %s,
                    "imageUrl" = COALESCE(%s, "imageUrl"),
                    "imageCaption" = COALESCE(NULLIF(%s, ''), "imageCaption"),
                    "updatedAt" = NOW()
                WHERE id = %s
                """,
                (
                    content,
                    parsed.get("image_url"),
                    parsed.get("image_caption"),
                    art_id,
                ),
            )
            conn.commit()
            img_count = content.count("<img")
            print(f"   ✅ {len(content)} chars, {img_count} image(s)")
            success += 1
        except Exception as exc:
            conn.rollback()
            print(f"   ❌ Erreur BDD: {exc}")

    cur.close()
    conn.close()
    print(f"\n[*] Terminé. {success}/{len(articles)} articles enrichis.")


if __name__ == "__main__":
    main()