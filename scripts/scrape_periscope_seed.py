"""Scraper dédié le-periscope.info — rattrapage via sitemap + filtre Mulhouse."""
import argparse
import json
import os
from datetime import datetime, timedelta, timezone
from xml.etree import ElementTree as ET

import psycopg2
from curl_cffi import requests
from dotenv import load_dotenv

from scrape_utils import (
    fetch_periscope_page,
    is_mulhouse_related,
    parse_periscope_article,
)

load_dotenv(".env.local")
load_dotenv(".env")

DATABASE_URL = os.environ.get("DATABASE_URL")
SOURCE = "Le Périscope"
SITEMAP_INDEX = "https://le-periscope.info/sitemap_index.xml"
SITEMAP_NS = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
SKIP_PATH_PARTS = (
    "/les-articles/",
    "/category/",
    "/author/",
    "/tag/",
    "/wp-content/",
    "/wp-json/",
)


def get_db_connection():
    if not DATABASE_URL:
        raise ValueError("DATABASE_URL non définie")
    clean_url = DATABASE_URL.replace("?pgbouncer=true", "").replace("&pgbouncer=true", "")
    return psycopg2.connect(clean_url)


def is_article_url(url: str) -> bool:
    if "le-periscope.info" not in url:
        return False
    if any(part in url for part in SKIP_PATH_PARTS):
        return False
    if url.rstrip("/").endswith(("le-periscope.info", "le-periscope.info/le-journal")):
        return False
    return "/le-journal/" in url or "/aperiscope/" in url


def fetch_post_sitemap_urls() -> list[str]:
    index_resp = requests.get(SITEMAP_INDEX, timeout=60, impersonate="chrome110")
    index_resp.raise_for_status()
    index_root = ET.fromstring(index_resp.text)

    sitemap_urls = []
    for loc in index_root.findall(".//sm:loc", SITEMAP_NS):
        if loc.text and "post-sitemap" in loc.text:
            sitemap_urls.append(loc.text)

    article_urls = []
    for sitemap_url in sitemap_urls:
        resp = requests.get(sitemap_url, timeout=60, impersonate="chrome110")
        resp.raise_for_status()
        root = ET.fromstring(resp.text)
        for url_el in root.findall("sm:url", SITEMAP_NS):
            loc_el = url_el.find("sm:loc", SITEMAP_NS)
            if loc_el is None or not loc_el.text:
                continue
            url = loc_el.text.strip()
            if is_article_url(url):
                article_urls.append(url)

    return list(dict.fromkeys(article_urls))


def fetch_sitemap_entries(days: int | None) -> list[dict]:
    index_resp = requests.get(SITEMAP_INDEX, timeout=60, impersonate="chrome110")
    index_resp.raise_for_status()
    index_root = ET.fromstring(index_resp.text)

    sitemap_urls = []
    for loc in index_root.findall(".//sm:loc", SITEMAP_NS):
        if loc.text and "post-sitemap" in loc.text:
            sitemap_urls.append(loc.text)

    cutoff = None
    if days and days > 0:
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)

    entries = []
    for sitemap_url in sitemap_urls:
        resp = requests.get(sitemap_url, timeout=60, impersonate="chrome110")
        resp.raise_for_status()
        root = ET.fromstring(resp.text)
        for url_el in root.findall("sm:url", SITEMAP_NS):
            loc_el = url_el.find("sm:loc", SITEMAP_NS)
            if loc_el is None or not loc_el.text:
                continue
            url = loc_el.text.strip()
            if not is_article_url(url):
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

    entries.sort(
        key=lambda item: item.get("lastmod") or datetime.min.replace(tzinfo=timezone.utc),
        reverse=True,
    )
    return entries


def get_existing_links(cur) -> set[str]:
    cur.execute('SELECT link FROM "Article" WHERE link LIKE %s', ("%le-periscope.info%",))
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
            stats["inserted"],
            stats["errors"],
            _json_safe_stats(stats),
        ),
    )
    conn.commit()


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
        "skipped_not_mulhouse": 0,
        "skipped_no_title": 0,
        "skipped_insufficient": 0,
        "errors": 0,
        "started_at": datetime.now(),
        "days": days,
    }

    print(f"[*] Sitemap articles: {len(entries)}")
    print(f"[*] Déjà en base: {len(existing)}")
    print(f"[*] À analyser: {len(missing)}")

    for i, entry in enumerate(missing, 1):
        url = entry["url"]
        stats["processed"] += 1
        if i % 25 == 0 or i == 1:
            print(f"[{i}/{len(missing)}] {url}")

        if dry_run:
            continue

        soup = fetch_periscope_page(url)
        if not soup:
            stats["errors"] += 1
            print(f"   ⚠️ Page inaccessible: {url}")
            continue

        parsed = parse_periscope_article(soup, url)
        title = parsed.get("title")
        content = parsed.get("content")
        description = parsed.get("description")

        if not title:
            stats["skipped_no_title"] += 1
            continue

        if not is_mulhouse_related(title, description, content):
            stats["skipped_not_mulhouse"] += 1
            continue

        if not content or len(content) < 100:
            stats["skipped_insufficient"] += 1
            print(f"   ⚠️ Contenu insuffisant: {title[:60]}")
            continue

        published_at = parsed.get("published_at")
        if not published_at and entry.get("lastmod"):
            published_at = entry["lastmod"].astimezone(timezone.utc).replace(tzinfo=None)
        if not published_at:
            published_at = datetime.now()

        try:
            insert_article(
                cur,
                {
                    "title": title,
                    "link": url,
                    "image_url": parsed.get("image_url"),
                    "image_caption": parsed.get("image_caption"),
                    "description": description or "",
                    "published_at": published_at,
                    "content": content,
                },
            )
            conn.commit()
            stats["inserted"] += 1
            print(f"   ✅ Inséré Mulhouse ({len(content)} chars): {title[:70]}")
        except psycopg2.errors.UniqueViolation:
            conn.rollback()
        except Exception as exc:
            conn.rollback()
            stats["errors"] += 1
            print(f"   ❌ Erreur insertion: {exc}")

    return stats


def main():
    parser = argparse.ArgumentParser(description="Scraper dédié le-periscope.info (filtre Mulhouse)")
    parser.add_argument(
        "--days",
        type=int,
        default=0,
        help="Limiter aux articles modifiés dans les N derniers jours (0 = tout le sitemap)",
    )
    parser.add_argument("--limit", type=int, default=0, help="Nombre max d'articles à traiter")
    parser.add_argument("--dry-run", action="store_true", help="Simulation sans écriture en base")
    args = parser.parse_args()

    limit = args.limit if args.limit > 0 else None
    days = args.days if args.days > 0 else None

    print("[*] Démarrage du scraper dédié le-periscope.info...")
    conn = get_db_connection()
    cur = conn.cursor()

    try:
        stats = seed_missing_articles(cur, conn, days, limit, args.dry_run)
        print(
            f"\n[*] Terminé. Insérés: {stats['inserted']} | "
            f"Hors Mulhouse: {stats['skipped_not_mulhouse']} | "
            f"Contenu insuffisant: {stats['skipped_insufficient']} | "
            f"Erreurs: {stats['errors']}"
        )

        if not args.dry_run:
            status = "SUCCESS" if stats["errors"] == 0 else "WARNING"
            log_scraping(cur, conn, stats, status)
    finally:
        cur.close()
        conn.close()


if __name__ == "__main__":
    main()