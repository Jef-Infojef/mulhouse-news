#!/usr/bin/env python3
"""Scrape les agendas (M+ Info, m2A le mag, JDS.fr) vers la table Outing."""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
from datetime import datetime, timedelta, timezone

from dotenv import load_dotenv

from outing_scrape_utils import (
    ParsedEvent,
    ScrapeStats,
    add_error,
    decode_html_entities,
    ensure_category,
    extract_json_ld,
    extract_meta,
    fetch_text,
    format_image,
    format_location,
    format_price,
    get_association_id,
    get_db_connection,
    is_event_type,
    is_within_ahead_window,
    log_scrape,
    parse_iso_date,
    record_result,
    sleep_ms,
    strip_html,
    upsert_outing,
)

load_dotenv(".env.local")
load_dotenv(".env")

MPLUS_SITEMAP = "https://www.mplusinfo.fr/sitemap_events.xml"
MPLUS_HOST = "mplusinfo.fr"
MPLUS_CATEGORY = ("mplusinfo", "M+ Info", "#7c3aed")

MAG_SITEMAP_INDEX = "https://mag.mulhouse-alsace.fr/sitemap_index.xml"
MAG_HOST = "mag.mulhouse-alsace.fr"
MAG_CATEGORY = ("m2a-le-mag", "m2A le mag", "#0d9488")

JDS_AGENDA_INDEX = "https://www.jds.fr/mulhouse/agenda/"
JDS_HOST = "jds.fr"
JDS_CATEGORY = ("jds", "JDS.fr", "#f59e0b")

FETCH_DELAY_MS = 450
JDS_FETCH_DELAY_MS = 350


def parse_url_event_date(url: str) -> datetime | None:
    match = re.search(r"/evenements/(\d{4})/(\d{2})/(\d{2})/", url)
    if not match:
        return None
    year, month, day = map(int, match.groups())
    return datetime(year, month, day, tzinfo=timezone.utc)


def parse_mplus_event_page(html: str, page_url: str) -> ParsedEvent | None:
    json_ld_items = extract_json_ld(html)
    event_json_ld = next(
        (
            item
            for item in json_ld_items
            if item.get("@type") in ("Event", "SocialEvent", "TheaterEvent")
        ),
        None,
    )

    h1_match = re.search(r"<h1[^>]*>([^<]+)</h1>", html, re.IGNORECASE)
    title_raw = (
        (event_json_ld or {}).get("name")
        or extract_meta(html, "og:title")
        or (h1_match.group(1) if h1_match else None)
    )
    if not title_raw:
        return None

    title = decode_html_entities(re.sub(r"\s*\|\s*M\+\s*$", "", str(title_raw), flags=re.IGNORECASE).strip())
    start_date = parse_iso_date((event_json_ld or {}).get("startDate")) or parse_iso_date(
        extract_meta(html, "event:start_time")
    )
    end_date = parse_iso_date((event_json_ld or {}).get("endDate")) or parse_iso_date(
        extract_meta(html, "event:end_time")
    )
    url_date = parse_url_event_date(page_url)
    date = start_date or url_date
    if not date:
        return None
    if end_date and end_date < date:
        return None

    description = (event_json_ld or {}).get("description") or extract_meta(html, "og:description")
    if description:
        description = decode_html_entities(str(description)).strip()

    external_url = (event_json_ld or {}).get("url")
    if isinstance(external_url, str) and MPLUS_HOST not in external_url:
        suffix = f"Plus d'infos : {external_url}"
        description = f"{description}\n\n{suffix}" if description else suffix

    image_url = format_image((event_json_ld or {}).get("image")) or extract_meta(html, "og:image")

    return ParsedEvent(
        title=title,
        description=description[:2000] if description else None,
        image_url=image_url,
        date=date,
        end_date=end_date,
        location=format_location((event_json_ld or {}).get("location")),
        price=format_price((event_json_ld or {}).get("offers")),
        link=page_url,
    )


def fetch_mplus_sitemap_entries() -> list[dict]:
    xml = fetch_text(MPLUS_SITEMAP, sitemap=True)
    entries = []
    for match in re.finditer(r"<loc>([^<]+)</loc>", xml):
        url = match.group(1).strip()
        if MPLUS_HOST not in url or "/evenements/" not in url:
            continue
        entries.append({"url": url, "url_date": parse_url_event_date(url)})
    return entries


def filter_mplus_entries(entries: list[dict], past_days: int, ahead_days: int) -> list[dict]:
    now = datetime.now(timezone.utc)
    start_of_today = datetime(now.year, now.month, now.day, tzinfo=timezone.utc)
    min_date = start_of_today - timedelta(days=past_days)
    max_date = start_of_today + timedelta(days=ahead_days) if ahead_days > 0 else None

    filtered = []
    for entry in entries:
        url_date = entry.get("url_date")
        if not url_date:
            filtered.append(entry)
            continue
        if url_date < min_date:
            continue
        if max_date and url_date > max_date:
            continue
        filtered.append(entry)
    return filtered


def clean_mag_title(title: str) -> str:
    cleaned = decode_html_entities(title)
    cleaned = re.sub(r"\s*[-|]\s*m2a le mag\s*$", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s*[-|]\s*mulhouse alsace\s*$", "", cleaned, flags=re.IGNORECASE)
    return cleaned.strip()


def is_mag_event_url(url: str) -> bool:
    if MAG_HOST not in url or "/evenement/" not in url:
        return False
    path = url.replace(f"https://{MAG_HOST}/", "").replace(f"http://{MAG_HOST}/", "").rstrip("/")
    if not path or path in ("evenement", "evenements"):
        return False
    if not path.startswith("evenement/"):
        return False
    return len(path.split("/")) >= 2


def parse_mag_event_page(html: str, page_url: str) -> ParsedEvent | None:
    json_ld_items = extract_json_ld(html)
    event_json_ld = next((item for item in json_ld_items if is_event_type(item.get("@type"))), None)

    h1_match = re.search(r"<h1[^>]*>([^<]+)</h1>", html, re.IGNORECASE)
    title_raw = (
        (event_json_ld or {}).get("name")
        or extract_meta(html, "og:title")
        or (h1_match.group(1) if h1_match else None)
    )
    if not title_raw:
        return None

    event_status = str((event_json_ld or {}).get("eventStatus") or "")
    if "Cancelled" in event_status or "Postponed" in event_status:
        return None

    start_date = parse_iso_date((event_json_ld or {}).get("startDate")) or parse_iso_date(
        extract_meta(html, "event:start_time")
    )
    end_date = parse_iso_date((event_json_ld or {}).get("endDate")) or parse_iso_date(
        extract_meta(html, "event:end_time")
    )
    if not start_date:
        return None
    if end_date and end_date < start_date:
        return None

    description = (event_json_ld or {}).get("description") or extract_meta(html, "og:description")
    if description:
        description = strip_html(str(description))

    return ParsedEvent(
        title=clean_mag_title(str(title_raw)),
        description=description[:2000] if description else None,
        image_url=format_image((event_json_ld or {}).get("image")) or extract_meta(html, "og:image"),
        date=start_date,
        end_date=end_date,
        location=format_location((event_json_ld or {}).get("location")),
        price=format_price((event_json_ld or {}).get("offers")),
        link=page_url,
    )


def fetch_mag_sitemap_entries() -> list[dict]:
    index_xml = fetch_text(MAG_SITEMAP_INDEX, sitemap=True)
    sitemap_urls = []
    for match in re.finditer(r"<loc>([^<]+)</loc>", index_xml):
        url = match.group(1).strip()
        if (
            "tribe_events-sitemap" in url
            and "tribe_events_cat" not in url
            and "tec_recurring_events" not in url
        ):
            sitemap_urls.append(url)

    entries = []
    seen: set[str] = set()
    for sitemap_url in sitemap_urls:
        xml = fetch_text(sitemap_url, sitemap=True)
        for block_match in re.finditer(r"<url>([\s\S]*?)</url>", xml):
            block = block_match.group(1)
            loc_match = re.search(r"<loc>([^<]+)</loc>", block)
            if not loc_match:
                continue
            loc = loc_match.group(1).strip()
            if not is_mag_event_url(loc) or loc in seen:
                continue
            lastmod_match = re.search(r"<lastmod>([^<]+)</lastmod>", block)
            lastmod = parse_iso_date(lastmod_match.group(1)) if lastmod_match else None
            seen.add(loc)
            entries.append({"url": loc, "lastmod": lastmod})
    return entries


def filter_mag_entries(entries: list[dict], past_days: int) -> list[dict]:
    if past_days == 0:
        return entries
    now = datetime.now(timezone.utc)
    start_of_today = datetime(now.year, now.month, now.day, tzinfo=timezone.utc)
    min_date = start_of_today - timedelta(days=past_days)
    return [entry for entry in entries if not entry.get("lastmod") or entry["lastmod"] >= min_date]


def is_jds_event_url(url: str) -> bool:
    return JDS_HOST in url and ("/mulhouse/" in url or "/alsace/" in url)


def parse_jds_event_json_ld(item: dict) -> ParsedEvent | None:
    link = item.get("url")
    if not isinstance(link, str) or not is_jds_event_url(link.strip()):
        return None

    event_status = str(item.get("eventStatus") or "")
    if "Cancelled" in event_status or "Postponed" in event_status:
        return None

    title = decode_html_entities(str(item.get("name") or "")).strip()
    if not title:
        return None

    start_date = parse_iso_date(str(item.get("startDate") or ""))
    if not start_date:
        return None
    end_date = parse_iso_date(str(item.get("endDate"))) if item.get("endDate") else None
    if end_date and end_date < start_date:
        return None

    description = strip_html(str(item["description"])) if isinstance(item.get("description"), str) else None

    return ParsedEvent(
        title=title,
        description=description[:2000] if description else None,
        image_url=format_image(item.get("image")),
        date=start_date,
        end_date=end_date,
        location=format_location(item.get("location")),
        price=format_price(item.get("offers")),
        link=link.strip(),
    )


def extract_jds_agenda_category_urls(html: str) -> list[str]:
    urls: set[str] = set()
    for match in re.finditer(r"https://www\.jds\.fr(/mulhouse/[a-z0-9\-/]+-\d+_B)", html, re.IGNORECASE):
        if "/agenda/" in match.group(1):
            urls.add(f"https://www.jds.fr{match.group(1)}")
    for match in re.finditer(r'href="(/mulhouse/agenda/[^"]+?-\d+_B)"', html, re.IGNORECASE):
        urls.add(f"https://www.jds.fr{match.group(1)}")
    return sorted(urls)


def parse_jds_events_from_html(html: str) -> list[ParsedEvent]:
    events = []
    for item in extract_json_ld(html):
        if not is_event_type(item.get("@type")):
            continue
        parsed = parse_jds_event_json_ld(item)
        if parsed:
            events.append(parsed)
    return events


def scrape_mplus(
    past_days: int,
    ahead_days: int,
    limit: int | None,
    dry_run: bool,
) -> dict:
    start = time.time()
    stats = ScrapeStats(error_samples=[])
    association_id = get_association_id(required=not dry_run)

    all_entries = fetch_mplus_sitemap_entries()
    entries = filter_mplus_entries(all_entries, past_days, ahead_days)
    entries.sort(key=lambda item: (item.get("url_date") or datetime.min.replace(tzinfo=timezone.utc)), reverse=True)
    if limit and limit > 0:
        entries = entries[:limit]

    print(
        f"[M+ EVENTS] Sitemap: {len(all_entries)} | À traiter: {len(entries)} | association: {association_id}"
    )

    conn = None if dry_run else get_db_connection()
    try:
        cur = conn.cursor() if conn else None
        category_id = None
        if not dry_run:
            slug, name, color = MPLUS_CATEGORY
            category_id = ensure_category(cur, association_id, slug, name, color)
            conn.commit()

        for entry in entries:
            stats.processed += 1
            if stats.processed % 25 == 0:
                print(f"[M+ EVENTS] Progression {stats.processed}/{len(entries)}")

            try:
                html = fetch_text(entry["url"], timeout=20)
                parsed = parse_mplus_event_page(html, entry["url"])
                if not parsed:
                    stats.skipped += 1
                    continue
                result = upsert_outing(cur, association_id, category_id, parsed, dry_run=dry_run)
                record_result(stats, result)
                if conn:
                    conn.commit()
            except Exception as exc:
                add_error(stats, f"{entry['url']}: {exc}")
                if conn:
                    conn.rollback()

            sleep_ms(FETCH_DELAY_MS)

        duration = round(time.time() - start, 2)
        if cur and not dry_run:
            log_scrape(cur, "mplus-events", stats, duration, dry_run=dry_run)
            conn.commit()
    finally:
        if conn:
            conn.close()

    return build_result("mplus", stats, duration, len(all_entries), len(entries))


def scrape_mag(
    past_days: int,
    ahead_days: int,
    limit: int | None,
    dry_run: bool,
) -> dict:
    start = time.time()
    stats = ScrapeStats(error_samples=[])
    association_id = get_association_id(required=not dry_run)

    all_entries = fetch_mag_sitemap_entries()
    entries = filter_mag_entries(all_entries, past_days)
    entries.sort(key=lambda item: (item.get("lastmod") or datetime.min.replace(tzinfo=timezone.utc)), reverse=True)
    if limit and limit > 0:
        entries = entries[:limit]

    print(
        f"[MAG EVENTS] Sitemap: {len(all_entries)} | À traiter: {len(entries)} | association: {association_id}"
    )

    conn = None if dry_run else get_db_connection()
    try:
        cur = conn.cursor() if conn else None
        category_id = None
        if not dry_run:
            slug, name, color = MAG_CATEGORY
            category_id = ensure_category(cur, association_id, slug, name, color)
            conn.commit()

        for entry in entries:
            stats.processed += 1
            if stats.processed % 25 == 0:
                print(f"[MAG EVENTS] Progression {stats.processed}/{len(entries)}")

            try:
                html = fetch_text(entry["url"], timeout=20)
                parsed = parse_mag_event_page(html, entry["url"])
                if not parsed:
                    stats.skipped += 1
                    continue
                if not is_within_ahead_window(parsed.date, ahead_days):
                    stats.skipped += 1
                    continue
                result = upsert_outing(cur, association_id, category_id, parsed, dry_run=dry_run)
                record_result(stats, result)
                if conn:
                    conn.commit()
            except Exception as exc:
                add_error(stats, f"{entry['url']}: {exc}")
                if conn:
                    conn.rollback()

            sleep_ms(FETCH_DELAY_MS)

        duration = round(time.time() - start, 2)
        if cur and not dry_run:
            log_scrape(cur, "mag-events", stats, duration, dry_run=dry_run)
            conn.commit()
    finally:
        if conn:
            conn.close()

    return build_result("mag", stats, duration, len(all_entries), len(entries))


def scrape_jds(
    ahead_days: int,
    limit: int | None,
    dry_run: bool,
) -> dict:
    start = time.time()
    stats = ScrapeStats(error_samples=[])
    association_id = get_association_id(required=not dry_run)

    index_html = fetch_text(JDS_AGENDA_INDEX, timeout=30)
    category_urls = extract_jds_agenda_category_urls(index_html)
    if limit and limit > 0:
        category_urls = category_urls[:limit]

    print(
        f"[JDS EVENTS] Catégories agenda: {len(category_urls)} | association: {association_id}"
    )

    events_by_link: dict[str, ParsedEvent] = {}
    for index, category_url in enumerate(category_urls):
        if index == 0 or (index + 1) % 10 == 0:
            print(f"[JDS EVENTS] Catégories {index + 1}/{len(category_urls)}")

        try:
            html = fetch_text(category_url, timeout=25)
            for event in parse_jds_events_from_html(html):
                events_by_link[event.link] = event
        except Exception as exc:
            add_error(stats, f"{category_url}: {exc}")

        sleep_ms(JDS_FETCH_DELAY_MS)

    unique_events = list(events_by_link.values())
    print(f"[JDS EVENTS] Événements uniques: {len(unique_events)}")

    conn = None if dry_run else get_db_connection()
    try:
        cur = conn.cursor() if conn else None
        category_id = None
        if not dry_run:
            slug, name, color = JDS_CATEGORY
            category_id = ensure_category(cur, association_id, slug, name, color)
            conn.commit()

        for event in unique_events:
            stats.processed += 1
            if stats.processed % 50 == 0:
                print(f"[JDS EVENTS] Upsert {stats.processed}/{len(unique_events)}")

            if not is_within_ahead_window(event.date, ahead_days):
                stats.skipped += 1
                continue

            try:
                result = upsert_outing(cur, association_id, category_id, event, dry_run=dry_run)
                record_result(stats, result)
                if conn:
                    conn.commit()
            except Exception as exc:
                add_error(stats, f"{event.link}: {exc}")
                if conn:
                    conn.rollback()

        duration = round(time.time() - start, 2)
        if cur and not dry_run:
            log_scrape(cur, "jds-events", stats, duration, dry_run=dry_run)
            conn.commit()
    finally:
        if conn:
            conn.close()

    result = build_result("jds", stats, duration, len(category_urls), len(unique_events))
    result["categories"] = len(category_urls)
    return result


def build_result(source: str, stats: ScrapeStats, duration: float, total: int, to_process: int) -> dict:
    return {
        "source": source,
        "success": stats.errors == 0,
        "total": total,
        "to_process": to_process,
        "processed": stats.processed,
        "inserted": stats.inserted,
        "updated": stats.updated,
        "skipped": stats.skipped,
        "errors": stats.errors,
        "duration": duration,
        "error_samples": stats.error_samples or None,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Scrape agendas vers Outing (Sorties)")
    parser.add_argument(
        "--source",
        choices=["mplus", "mag", "jds", "all"],
        default="all",
        help="Source à scraper (défaut: all)",
    )
    parser.add_argument("--past-days", type=int, default=7, help="Fenêtre passée (mplus/mag)")
    parser.add_argument("--ahead-days", type=int, default=120, help="Fenêtre future")
    parser.add_argument("--limit", type=int, default=None, help="Limiter le nombre d'entrées")
    parser.add_argument("--dry-run", action="store_true", help="Ne pas écrire en base")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    sources = ["mplus", "mag", "jds"] if args.source == "all" else [args.source]
    results = []
    had_errors = False

    runners = {
        "mplus": lambda: scrape_mplus(args.past_days, args.ahead_days, args.limit, args.dry_run),
        "mag": lambda: scrape_mag(args.past_days, args.ahead_days, args.limit, args.dry_run),
        "jds": lambda: scrape_jds(args.ahead_days, args.limit, args.dry_run),
    }

    for source in sources:
        print(f"\n=== Scraping {source} ===")
        result = runners[source]()
        results.append(result)
        print(json.dumps(result, indent=2, ensure_ascii=False))
        if not result["success"]:
            had_errors = True

    if had_errors:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())