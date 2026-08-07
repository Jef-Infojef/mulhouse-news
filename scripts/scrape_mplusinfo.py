"""Scraper dédié mplusinfo.fr — ingestion via sitemap + contenu complet."""
import argparse
import json
import os
from datetime import datetime, timedelta, timezone
from xml.etree import ElementTree as ET

import psycopg2
from curl_cffi import requests
from dotenv import load_dotenv

from scrape_utils import fetch_mplusinfo_page, parse_mplusinfo_article

load_dotenv(".env.local")
load_dotenv(".env")

DATABASE_URL = os.environ.get("DATABASE_URL")
SOURCE = "mplusinfo.fr"
SITEMAP_URL = "https://www.mplusinfo.fr/sitemap_contents.xml"
SITEMAP_NS = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}


def get_db_connection():
    if not DATABASE_URL:
        raise ValueError("DATABASE_URL non définie")
    clean_url = DATABASE_URL.replace("?pgbouncer=true", "").replace("&pgbouncer=true", "")
    return psycopg2.connect(clean_url)


def fetch_sitemap_entries(days: int | None) -> list[dict]:
    resp = requests.get(SITEMAP_URL, timeout=60, impersonate="chrome110")
    resp.raise_for_status()
    root = ET.fromstring(resp.text)

    cutoff = None
    if days and days > 0:
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)

    entries = []
    for url_el in root.findall("sm:url", SITEMAP_NS):
        loc_el = url_el.find("sm:loc", SITEMAP_NS)
        if loc_el is None or not loc_el.text:
            continue
        url = loc_el.text.strip()
        if "mplusinfo.fr" not in url:
            continue

        lastmod = None
        lastmod_el = url_el.find("sm:lastmod", SITEMAP_NS)
        if lastmod_el is not None and lastmod_el.text:
            try:
                lastmod = datetime.fromisoformat(lastmod_el.text.replace("Z", "+00:00"))
            except ValueError:
                lastmod = None

        if cutoff and lastmod and lastmod < cutoff:
            continue

        entries.append({"url": url, "lastmod": lastmod})

    entries.sort(key=lambda item: item.get("lastmod") or datetime.min.replace(tzinfo=timezone.utc), reverse=True)
    return entries


def get_existing_links(cur) -> set[str]:
    cur.execute('SELECT link FROM "Article" WHERE link LIKE %s', ("%mplusinfo.fr%",))
    return {row[0] for row in cur.fetchall()}


def insert_article(cur, data: dict) -> str | None:
    cur.execute(
        """
        INSERT INTO "Article" (
            id, title, link, "imageUrl", "imageCaption", source,
            description, "publishedAt", content, "updatedAt"
        )
        VALUES (gen_random_uuid(), %s, %s, %s, %s, %s, %s, %s, %s, NOW())
        RETURNING id
        """,
        (
            data["title"],
            data["link"],
            data.get("image_url"),
            data.get("image_caption"),
            SOURCE,
            data.get("description") or "",
            data["published_at"],
            data.get("content"),
        ),
    )
    row = cur.fetchone()
    return row[0] if row else None


def update_article_content(cur, article_id: str, content: str, image_caption: str | None):
    cur.execute(
        """
        UPDATE "Article"
        SET content = %s,
            "imageCaption" = COALESCE("imageCaption", %s),
            "updatedAt" = NOW()
        WHERE id = %s
        """,
        (content, image_caption, article_id),
    )


def _json_safe_stats(stats: dict) -> str:
    safe = {}
    for key, value in stats.items():
        if isinstance(value, datetime):
            safe[key] = value.isoformat()
        else:
            safe[key] = value
    return json.dumps(safe)


def log_scraping(cur, conn, stats: dict, status: str):
    cur.execute(
        """
        INSERT INTO "ScrapingLog" (
            id, "startedAt", "finishedAt", status, "articlesCount",
            "successCount", "errorCount", details
        )
        VALUES (gen_random_uuid(), %s, %s, %s, %s, %s, %s, %s)
        """,
        (
            stats["started_at"],
            datetime.now(),
            status,
            stats["processed"],
            stats["inserted"] + stats["updated"],
            stats["errors"],
            _json_safe_stats(stats),
        ),
    )
    conn.commit()


def backfill_missing_content(cur, conn, limit: int | None, dry_run: bool) -> dict:
    query = """
        SELECT id, title, link
        FROM "Article"
        WHERE link LIKE '%%mplusinfo.fr%%'
          AND (content IS NULL OR LENGTH(content) < 100)
        ORDER BY "publishedAt" DESC
    """
    if limit:
        query += f" LIMIT {int(limit)}"

    cur.execute(query)
    rows = cur.fetchall()
    stats = {
        "mode": "backfill_content",
        "processed": 0,
        "inserted": 0,
        "updated": 0,
        "skipped": 0,
        "errors": 0,
        "started_at": datetime.now(),
    }

    print(f"[*] {len(rows)} articles mplusinfo.fr sans contenu à rattraper.")
    for i, (article_id, title, link) in enumerate(rows, 1):
        stats["processed"] += 1
        print(f"[{i}/{len(rows)}] {title[:60]}...")

        if dry_run:
            continue

        soup = fetch_mplusinfo_page(link)
        if not soup:
            stats["errors"] += 1
            print("   ⚠️ Page inaccessible")
            continue

        parsed = parse_mplusinfo_article(soup, link)
        content = parsed.get("content")
        if not content or len(content) < 100:
            stats["errors"] += 1
            print("   ⚠️ Contenu insuffisant")
            continue

        try:
            update_article_content(cur, article_id, content, parsed.get("image_caption"))
            conn.commit()
            stats["updated"] += 1
            print(f"   ✅ Contenu mis à jour ({len(content)} chars)")
        except Exception as exc:
            conn.rollback()
            stats["errors"] += 1
            print(f"   ❌ Erreur BDD: {exc}")

    return stats


def seed_missing_articles(cur, conn, days: int | None, limit: int | None, dry_run: bool) -> dict:
    entries = fetch_sitemap_entries(days)
    existing = get_existing_links(cur)
    missing = [entry for entry in entries if entry["url"] not in existing]

    if limit:
        missing = missing[:limit]

    stats = {
        "mode": "seed",
        "sitemap_total": len(entries),
        "already_in_db": len(existing),
        "to_process": len(missing),
        "processed": 0,
        "inserted": 0,
        "updated": 0,
        "skipped": 0,
        "errors": 0,
        "started_at": datetime.now(),
        "days": days,
    }

    print(f"[*] Sitemap: {len(entries)} URLs")
    print(f"[*] Déjà en base: {len(existing)}")
    print(f"[*] À importer: {len(missing)}")

    for i, entry in enumerate(missing, 1):
        url = entry["url"]
        stats["processed"] += 1
        print(f"[{i}/{len(missing)}] {url}")

        if dry_run:
            continue

        soup = fetch_mplusinfo_page(url)
        if not soup:
            stats["errors"] += 1
            print("   ⚠️ Page inaccessible")
            continue

        parsed = parse_mplusinfo_article(soup, url)
        title = parsed.get("title")
        published_at = parsed.get("published_at")

        if not title:
            stats["errors"] += 1
            print("   ⚠️ Titre introuvable")
            continue

        if not published_at and entry.get("lastmod"):
            published_at = entry["lastmod"].astimezone(timezone.utc).replace(tzinfo=None)

        if not published_at:
            published_at = datetime.now()

        try:
            article_id = insert_article(
                cur,
                {
                    "title": title,
                    "link": url,
                    "image_url": parsed.get("image_url"),
                    "image_caption": parsed.get("image_caption"),
                    "description": parsed.get("description") or "",
                    "published_at": published_at,
                    "content": parsed.get("content"),
                },
            )
            conn.commit()
            stats["inserted"] += 1
            content_len = len(parsed.get("content") or "")
            print(f"   ✅ Inséré ({content_len} chars)")
            if not article_id:
                stats["errors"] += 1
        except psycopg2.errors.UniqueViolation:
            conn.rollback()
            stats["skipped"] += 1
            print("   ↪ Déjà présent (doublon)")
        except Exception as exc:
            conn.rollback()
            stats["errors"] += 1
            print(f"   ❌ Erreur insertion: {exc}")

    return stats


def main():
    parser = argparse.ArgumentParser(description="Scraper dédié mplusinfo.fr")
    parser.add_argument(
        "--days",
        type=int,
        default=0,
        help="Limiter aux articles modifiés dans les N derniers jours (0 = tout le sitemap)",
    )
    parser.add_argument("--limit", type=int, default=0, help="Nombre max d'articles à traiter")
    parser.add_argument("--dry-run", action="store_true", help="Simulation sans écriture en base")
    parser.add_argument(
        "--backfill-content",
        action="store_true",
        help="Rattraper le contenu des articles mplusinfo.fr déjà en base",
    )
    args = parser.parse_args()

    limit = args.limit if args.limit > 0 else None
    days = args.days if args.days > 0 else None

    print("[*] Démarrage du scraper dédié mplusinfo.fr...")
    conn = get_db_connection()
    cur = conn.cursor()

    try:
        if args.backfill_content:
            stats = backfill_missing_content(cur, conn, limit, args.dry_run)
        else:
            stats = seed_missing_articles(cur, conn, days, limit, args.dry_run)

        print(
            f"\n[*] Terminé. Insérés: {stats['inserted']} | "
            f"Mis à jour: {stats['updated']} | Erreurs: {stats['errors']}"
        )

        if not args.dry_run:
            status = "SUCCESS" if stats["errors"] == 0 else "WARNING"
            log_scraping(cur, conn, stats, status)
    finally:
        cur.close()
        conn.close()


if __name__ == "__main__":
    main()