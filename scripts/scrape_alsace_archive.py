"""Scraper d'archive L'Alsace via les sitemaps quotidiens (2006 → aujourd'hui).

Contourne Google News RSS (limité aux articles récents) en interrogeant
directement l'index de sitemaps du site :
    https://www.lalsace.fr/sitemap-index.xml
→ ~6 340 sitemaps journaliers `sitemap-YYYY-MM-DD.xml`, chacun contenant
  l'ensemble des URLs publiées ce jour-là (dont les plus anciennes).

Les articles détectés (titre dérivé du slug, publishedAt = lastmod) sont
insérés avec content = NULL ; le contenu est ensuite rempli par
`scrape_content_full.py --archive` (API GRDC + cookie EBRA).

Usage :
    python scripts/scrape_alsace_archive.py                     # tout (2006 → hier)
    python scripts/scrape_alsace_archive.py --start 2010-01-01 --end 2012-12-31
    python scripts/scrape_alsace_archive.py --filter mulhouse   # défaut (slug + chemin)
    python scripts/scrape_alsace_archive.py --check-page        # fil d'Ariane / 68224 sur les URL rejetées
    python scripts/scrape_alsace_archive.py --dry-run           # comptage seul
    python scripts/scrape_alsace_archive.py --limit 100         # insertion plafonnée

Rattrapage Grand Rex (2013-11-09), fil d'Ariane « Edition Mulhouse - Thann » :
    python scripts/scrape_alsace_archive.py --start 2013-11-09 --end 2013-11-09 --check-page

Backend : Convex si CONVEX_DEPLOY_KEY + NEXT_PUBLIC_CONVEX_URL sont définies,
sinon Supabase via DATABASE_URL (comme scrape_and_seed.py).
"""

import argparse
import json
import os
import random
import re
import sys
import time
import uuid
from datetime import date, datetime, timedelta, timezone

from curl_cffi import requests as curl_requests
import psycopg2
from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import convex_client
from scrape_utils import html_is_mulhouse_edition, is_mulhouse_url

load_dotenv()

SITEMAP_INDEX = "https://www.lalsace.fr/sitemap-index.xml"
SOURCE = "L'Alsace (archive)"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"
NS = "{http://www.sitemaps.org/schemas/sitemap/0.9}"
# URLs déjà ouvertes et hors édition Mulhouse : ne pas re-HTTP à chaque cron 15 min
REJECTED_KEY = "ALSACE_SITEMAP_NOT_MULHOUSE"
REJECTED_TTL_DAYS = 7


def title_from_slug(slug: str) -> str:
    """Titre lisible dérivé du slug d'URL (les sitemaps ne fournissent pas de titre)."""
    slug = re.sub(r"\(.*?\)", "", slug)
    words = [w for w in slug.split("-") if w]
    return " ".join(words).strip().capitalize() if words else "Sans titre"


def fetch_sitemap(url: str) -> str | None:
    for attempt in range(3):
        try:
            resp = curl_requests.get(url, timeout=30, impersonate="chrome110", headers={"User-Agent": UA})
            if resp.status_code == 200:
                return resp.text
            print(f"    [!] HTTP {resp.status_code} ({url})")
        except Exception as e:
            print(f"    [!] Erreur réseau ({url}): {e}")
        time.sleep(random.uniform(1.5, 3.5))
    return None


def list_daily_sitemaps(start: date, end: date) -> list[str]:
    xml = fetch_sitemap(SITEMAP_INDEX)
    if not xml:
        raise RuntimeError("Impossible de récupérer l'index de sitemaps")
    urls = re.findall(r"<loc>(https://www\.lalsace\.fr/sitemap-(\d{4}-\d{2}-\d{2})\.xml)</loc>", xml)
    selected = []
    for url, day in urls:
        try:
            d = datetime.strptime(day, "%Y-%m-%d").date()
        except ValueError:
            continue
        if start <= d <= end:
            selected.append((d, url))
    selected.sort()
    print(f"[*] {len(selected)} sitemaps journaliers entre {start} et {end}")
    return [url for _, url in selected]


def parse_sitemap(xml: str) -> list[dict]:
    entries = []
    for loc, lastmod in re.findall(r"<url><loc>([^<]+)</loc><lastmod>([^<]+)</lastmod>", xml):
        m = re.search(r"/\d{4}/\d{2}/\d{2}/([a-z0-9-]+)$", loc)
        if not m:
            continue
        published_at = None
        try:
            published_at = datetime.fromisoformat(lastmod)
        except ValueError:
            dm = re.search(r"/(\d{4})/(\d{2})/(\d{2})/", loc)
            if dm:
                try:
                    published_at = datetime(int(dm.group(1)), int(dm.group(2)), int(dm.group(3)))
                except ValueError:
                    pass
        entries.append({
            "link": loc,
            "title": title_from_slug(m.group(1)),
            "publishedAt": published_at,
        })
    return entries


def get_db_connection():
    url = os.environ.get("DATABASE_URL", "").replace("?pgbouncer=true", "").replace("&pgbouncer=true", "")
    return psycopg2.connect(url)


def sql_links_exist(cur, links: list[str]) -> set:
    if not links:
        return set()
    placeholders = ",".join(["%s"] * len(links))
    cur.execute(f'SELECT link FROM "Article" WHERE link IN ({placeholders})', links)
    return {row[0] for row in cur.fetchall()}


def load_rejected_urls(use_convex: bool, cur) -> dict:
    raw = None
    try:
        if use_convex:
            raw = convex_client.get_app_config(REJECTED_KEY)
        elif cur:
            cur.execute('SELECT value FROM "AppConfig" WHERE key = %s', (REJECTED_KEY,))
            row = cur.fetchone()
            raw = row[0] if row else None
    except Exception as e:
        print(f"[!] Cache fil d'Ariane illisible : {e}")
        return {}
    if not raw:
        return {}
    try:
        data = json.loads(raw)
        if not isinstance(data, dict):
            return {}
    except Exception:
        return {}
    cutoff = datetime.now(timezone.utc) - timedelta(days=REJECTED_TTL_DAYS)
    live = {}
    for url, iso in data.items():
        try:
            until = datetime.fromisoformat(iso)
            if until.tzinfo is None:
                until = until.replace(tzinfo=timezone.utc)
            if until >= cutoff:
                live[url] = iso
        except ValueError:
            continue
    return live


def persist_rejected_urls(use_convex: bool, conn, cur, rejected: dict):
    cutoff = datetime.now(timezone.utc) - timedelta(days=REJECTED_TTL_DAYS)
    drop = []
    for url, iso in rejected.items():
        try:
            until = datetime.fromisoformat(iso)
            if until.tzinfo is None:
                until = until.replace(tzinfo=timezone.utc)
            if until < cutoff:
                drop.append(url)
        except ValueError:
            drop.append(url)
    for url in drop:
        del rejected[url]
    payload = json.dumps(rejected)
    try:
        if use_convex:
            convex_client.set_app_config(REJECTED_KEY, payload)
        elif cur and conn:
            cur.execute(
                'INSERT INTO "AppConfig" (key, value, "updatedAt") VALUES (%s, %s, NOW()) '
                'ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value, "updatedAt" = NOW()',
                (REJECTED_KEY, payload),
            )
            conn.commit()
    except Exception as e:
        print(f"[!] Cache fil d'Ariane non persisté : {e}")


def lookup_existing(use_convex: bool, cur, links: list[str]) -> set[str]:
    if not links:
        return set()
    if use_convex:
        return convex_client.get_existing_links_for(links)
    return sql_links_exist(cur, links)


def insert_sql(cur, conn, row: dict) -> bool:
    cur.execute(
        """
        INSERT INTO "Article" (id, title, link, source, "publishedAt", "updatedAt")
        VALUES (gen_random_uuid(), %s, %s, %s, %s, NOW())
        """,
        (row["title"], row["link"], SOURCE, row["publishedAt"]),
    )
    conn.commit()
    return True


def main():
    parser = argparse.ArgumentParser(description="Backfill L'Alsace via sitemaps quotidiens")
    parser.add_argument("--start", type=str, default="2006-08-21", help="Date de début (YYYY-MM-DD)")
    parser.add_argument("--end", type=str, default=None, help="Date de fin (YYYY-MM-DD), défaut : hier")
    parser.add_argument("--filter", type=str, default="mulhouse", choices=["mulhouse", "all"],
                        help="Filtre des URLs : 'mulhouse' (défaut : slug + chemin d'édition) ou 'all'")
    parser.add_argument(
        "--check-page",
        action="store_true",
        help="Pour les URL hors filtre slug/chemin, ouvrir la page et garder "
        "celles dont le fil d'Ariane est l'édition Mulhouse-Thann (ou geo 68224). "
        "Le kicker « Centre-ville » seul ne suffit pas.",
    )
    parser.add_argument("--dry-run", action="store_true", help="Compte les candidats sans rien insérer")
    parser.add_argument("--limit", type=int, default=0, help="Plafonne le nombre d'insertions (0 = illimité)")
    args = parser.parse_args()

    try:
        start = datetime.strptime(args.start, "%Y-%m-%d").date()
    except ValueError:
        print(f"❌ Date de début invalide : {args.start}")
        sys.exit(1)
    end = datetime.strptime(args.end, "%Y-%m-%d").date() if args.end else date.today() - timedelta(days=1)

    use_convex = convex_client.use_convex()
    conn = cur = None
    if not use_convex and not args.dry_run:
        try:
            conn = get_db_connection()
            cur = conn.cursor()
        except Exception as e:
            print(f"❌ Connexion DB impossible : {e}")
            sys.exit(1)
    print(f"[*] Backend : {'Convex (cloud)' if use_convex else 'Supabase (psycopg2)'}")

    sitemaps = list_daily_sitemaps(start, end)
    inserted = skipped = errors = 0
    start_time = datetime.now()
    rejected = {} if args.dry_run else load_rejected_urls(use_convex, cur)
    check_skipped_cache = 0
    check_fetched = 0

    for i, sm_url in enumerate(sitemaps, 1):
        xml = fetch_sitemap(sm_url)
        if not xml:
            errors += 1
            continue
        parsed = parse_sitemap(xml)
        if args.filter == "all":
            entries = parsed
        else:
            entries = [e for e in parsed if is_mulhouse_url(e["link"])]
            if args.check_page:
                rest = [e for e in parsed if not is_mulhouse_url(e["link"])]
                if not args.dry_run:
                    already = lookup_existing(use_convex, cur, [e["link"] for e in rest])
                    rest = [e for e in rest if e["link"] not in already]
                now_iso = datetime.now(timezone.utc).isoformat()
                to_fetch = []
                for e in rest:
                    cached = rejected.get(e["link"])
                    if cached:
                        check_skipped_cache += 1
                        continue
                    to_fetch.append(e)
                kept_page = 0
                for j, e in enumerate(to_fetch, 1):
                    html = fetch_sitemap(e["link"])
                    check_fetched += 1
                    if html and html_is_mulhouse_edition(html):
                        entries.append(e)
                        kept_page += 1
                        rejected.pop(e["link"], None)
                    else:
                        rejected[e["link"]] = now_iso
                    if j % 20 == 0 or j == len(to_fetch):
                        print(
                            f"    fil d'Ariane {j}/{len(to_fetch)} — retenus +{kept_page} "
                            f"(cache {check_skipped_cache})"
                        )
                    time.sleep(random.uniform(0.25, 0.55))
        if not entries:
            continue
        print(f"[{i}/{len(sitemaps)}] {sm_url.split('/')[-1]} : {len(entries)} candidats Mulhouse")

        if args.dry_run:
            inserted += len(entries)
            continue

        existing = lookup_existing(use_convex, cur, [e["link"] for e in entries])

        for e in entries:
            if e["link"] in existing or (args.limit and inserted >= args.limit):
                skipped += 1
                continue
            try:
                if use_convex:
                    convex_client.upsert_article({
                        "title": e["title"],
                        "link": e["link"],
                        "source": SOURCE,
                        "publishedAt": int(e["publishedAt"].timestamp() * 1000) if e["publishedAt"] else None,
                        "updatedAt": int(time.time() * 1000),
                        "supabaseId": str(uuid.uuid4()),
                    })
                else:
                    insert_sql(cur, conn, e)
                inserted += 1
            except Exception as ex:
                errors += 1
                print(f"    [!] Insertion échouée ({e['link']}): {ex}")
                if not use_convex:
                    conn.rollback()
            time.sleep(random.uniform(0.15, 0.4))

        if args.limit and inserted >= args.limit:
            print(f"[*] Limite atteinte ({args.limit}) — arrêt.")
            break

    label = "candidats" if args.dry_run else "articles insérés"
    print(f"\n[*] TERMINÉ : {inserted} {label}, {skipped} déjà présents/ignorés, {errors} erreurs.")
    if args.check_page:
        print(
            f"[*] Fil d'Ariane : {check_fetched} pages ouvertes, "
            f"{check_skipped_cache} déjà hors-Mulhouse (cache {REJECTED_TTL_DAYS} j)"
        )
    if not args.dry_run:
        persist_rejected_urls(use_convex, conn, cur, rejected)

    if not args.dry_run and inserted > 0:
        try:
            details = json.dumps({"sitemaps": len(sitemaps), "skipped": skipped, "errors": errors})
            if use_convex:
                convex_client.insert_scraping_log(start_time, datetime.now(), status="SUCCESS",
                                                  articles_count=len(sitemaps), success_count=inserted,
                                                  error_count=errors, details=details)
            else:
                cur.execute("""
                    INSERT INTO "ScrapingLog" (id, "startedAt", "finishedAt", status, "articlesCount", "successCount", "errorCount", details)
                    VALUES (gen_random_uuid(), %s, %s, %s, %s, %s, %s, %s::jsonb)
                """, (start_time, datetime.now(), "SUCCESS", len(sitemaps), inserted, errors, details))
                conn.commit()
            print("[*] Log sauvegardé en DB.")
        except Exception as e:
            print(f"[!] Erreur sauvegarde log : {e}")
            if not use_convex and conn:
                conn.rollback()

    if cur:
        cur.close()
    if conn:
        conn.close()


if __name__ == "__main__":
    main()