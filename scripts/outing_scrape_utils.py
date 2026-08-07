"""Utilitaires partagés pour le scraping d'agenda (Outing / Sorties)."""
from __future__ import annotations

import html as htmllib
import json
import os
import re
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

import psycopg2
from curl_cffi import requests

FETCH_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "fr-FR,fr;q=0.9",
}

SITEMAP_HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; MulhouseNewsBot/1.0)",
}


@dataclass
class ParsedEvent:
    title: str
    description: str | None
    image_url: str | None
    date: datetime
    end_date: datetime | None
    location: str | None
    price: str | None
    link: str


@dataclass
class ScrapeStats:
    processed: int = 0
    inserted: int = 0
    updated: int = 0
    skipped: int = 0
    errors: int = 0
    error_samples: list[str] | None = None


def get_database_url() -> str:
    url = os.environ.get("DATABASE_URL")
    if not url:
        raise ValueError("DATABASE_URL non définie")
    return url.replace("?pgbouncer=true", "").replace("&pgbouncer=true", "")


def get_association_id(*, required: bool = True) -> str:
    assoc_id = os.environ.get("ASSOCIATION_ID")
    if not assoc_id:
        if required:
            raise ValueError("ASSOCIATION_ID non définie")
        return "dry-run"
    return assoc_id


def get_db_connection():
    return psycopg2.connect(get_database_url())


def new_id() -> str:
    return str(uuid.uuid4())


def sleep_ms(ms: int) -> None:
    time.sleep(ms / 1000)


def decode_html_entities(text: str) -> str:
    return htmllib.unescape(text)


def strip_html(value: str) -> str:
    cleaned = re.sub(r"<[^>]+>", " ", value)
    return decode_html_entities(re.sub(r"\s+", " ", cleaned).strip())


def extract_meta(html: str, prop: str) -> str | None:
    patterns = [
        rf'<meta[^>]+property=["\']{prop}["\'][^>]+content=["\']([^"\']+)["\']',
        rf'<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']{prop}["\']',
    ]
    for pattern in patterns:
        match = re.search(pattern, html, re.IGNORECASE)
        if match:
            return match.group(1)
    return None


def flatten_json_ld(data) -> list[dict]:
    if not data or not isinstance(data, (dict, list)):
        return []
    if isinstance(data, list):
        return [item for sub in data for item in flatten_json_ld(sub)]
    if isinstance(data, dict):
        graph = data.get("@graph")
        if isinstance(graph, list):
            return [item for sub in graph for item in flatten_json_ld(sub)]
        return [data]
    return []


def extract_json_ld(html: str) -> list[dict]:
    results: list[dict] = []
    regex = re.compile(
        r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>([\s\S]*?)</script>',
        re.IGNORECASE,
    )
    for match in regex.finditer(html):
        try:
            data = json.loads(match.group(1))
            results.extend(flatten_json_ld(data))
        except (json.JSONDecodeError, TypeError):
            continue
    return results


def is_event_type(event_type) -> bool:
    if isinstance(event_type, str):
        return event_type == "Event" or event_type.endswith("Event")
    if isinstance(event_type, list):
        return any(is_event_type(value) for value in event_type)
    return False


def parse_iso_date(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        normalized = value.replace("Z", "+00:00")
        parsed = datetime.fromisoformat(normalized)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed
    except ValueError:
        return None


def format_location(location) -> str | None:
    if not location:
        return None
    if isinstance(location, str):
        return strip_html(location)

    if isinstance(location, dict):
        name = strip_html(location["name"]) if location.get("name") else None
        address = location.get("address")

        if address:
            if isinstance(address, str):
                addr = strip_html(address)
                return f"{name}, {addr}" if name else addr
            parts = [
                name,
                address.get("streetAddress"),
                " ".join(
                    part
                    for part in [address.get("postalCode"), address.get("addressLocality")]
                    if part
                ),
            ]
            joined = ", ".join(part for part in parts if part)
            return joined or None
        return name
    return None


def format_image(image) -> str | None:
    if not image:
        return None
    if isinstance(image, str):
        return image
    if isinstance(image, list):
        return format_image(image[0]) if image else None
    if isinstance(image, dict):
        return image.get("url")
    return None


def format_price(offers) -> str | None:
    if not offers:
        return None
    offer_list = offers if isinstance(offers, list) else [offers]
    if not offer_list:
        return None
    offer = offer_list[0]
    if not isinstance(offer, dict):
        return None
    price = offer.get("price")
    if price is None:
        return None
    if price in (0, "0"):
        return "Gratuit"
    currency = f" {offer['priceCurrency']}" if offer.get("priceCurrency") else "€"
    return f"{price}{currency}"


def is_within_ahead_window(start_date: datetime, ahead_days: int) -> bool:
    if not ahead_days or ahead_days <= 0:
        return True
    max_date = datetime.now(timezone.utc) + timedelta(days=ahead_days)
    start = start_date if start_date.tzinfo else start_date.replace(tzinfo=timezone.utc)
    return start <= max_date


def ensure_category(
    cur,
    association_id: str,
    slug: str,
    name: str,
    color: str,
) -> str:
    cur.execute(
        """
        SELECT id FROM "OutingCategory"
        WHERE "associationId" = %s AND slug = %s
        LIMIT 1
        """,
        (association_id, slug),
    )
    row = cur.fetchone()
    if row:
        return row[0]

    category_id = new_id()
    cur.execute(
        """
        INSERT INTO "OutingCategory" (id, "associationId", name, slug, color, "createdAt", "updatedAt")
        VALUES (%s, %s, %s, %s, %s, NOW(), NOW())
        """,
        (category_id, association_id, name, slug, color),
    )
    return category_id


def upsert_outing(
    cur,
    association_id: str,
    category_id: str | None,
    event: ParsedEvent,
    dry_run: bool = False,
) -> str:
    now = datetime.now(timezone.utc)
    effective_end = event.end_date or event.date
    if effective_end.tzinfo is None:
        effective_end = effective_end.replace(tzinfo=timezone.utc)
    if effective_end < now:
        return "skipped"

    if dry_run:
        return "inserted"

    cur.execute(
        'SELECT id FROM "Outing" WHERE link = %s LIMIT 1',
        (event.link,),
    )
    row = cur.fetchone()

    data = (
        event.title,
        event.description,
        event.image_url,
        event.date,
        event.end_date,
        event.location,
        event.price,
        event.link,
        False,
    )

    if row:
        outing_id = row[0]
        cur.execute(
            """
            UPDATE "Outing"
            SET title = %s, description = %s, "imageUrl" = %s, date = %s,
                "endDate" = %s, location = %s, price = %s, link = %s,
                hidden = %s, "updatedAt" = NOW()
            WHERE id = %s
            """,
            (*data, outing_id),
        )
        if category_id:
            cur.execute(
                """
                INSERT INTO "OutingTag" ("outingId", "categoryId")
                VALUES (%s, %s)
                ON CONFLICT DO NOTHING
                """,
                (outing_id, category_id),
            )
        return "updated"

    outing_id = new_id()
    cur.execute(
        """
        INSERT INTO "Outing" (
            id, "associationId", title, description, "imageUrl", date, "endDate",
            location, price, link, hidden, "createdAt", "updatedAt"
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
        """,
        (outing_id, association_id, *data),
    )
    if category_id:
        cur.execute(
            """
            INSERT INTO "OutingTag" ("outingId", "categoryId")
            VALUES (%s, %s)
            ON CONFLICT DO NOTHING
            """,
            (outing_id, category_id),
        )
    return "inserted"


def log_scrape(
    cur,
    scrape_type: str,
    stats: ScrapeStats,
    duration: float,
    dry_run: bool = False,
) -> None:
    if dry_run:
        return
    errors_text = None
    if stats.errors > 0:
        errors_text = f"{stats.errors} erreurs"
        if stats.error_samples:
            errors_text += "\n" + "\n".join(stats.error_samples)
    cur.execute(
        """
        INSERT INTO "ScrapeLog" (
            id, type, status, duration, "totalMovies", "totalScreenings", errors, "createdAt"
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, NOW())
        """,
        (
            new_id(),
            scrape_type,
            "success" if stats.errors == 0 else "failure",
            duration,
            stats.inserted,
            stats.updated,
            errors_text,
        ),
    )


def fetch_text(url: str, timeout: int = 60, sitemap: bool = False) -> str:
    headers = SITEMAP_HEADERS if sitemap else FETCH_HEADERS
    resp = requests.get(url, headers=headers, timeout=timeout, impersonate="chrome110")
    resp.raise_for_status()
    return resp.text


def record_result(stats: ScrapeStats, result: str) -> None:
    if result == "inserted":
        stats.inserted += 1
    elif result == "updated":
        stats.updated += 1
    else:
        stats.skipped += 1


def add_error(stats: ScrapeStats, message: str) -> None:
    stats.errors += 1
    if stats.error_samples is None:
        stats.error_samples = []
    if len(stats.error_samples) < 10:
        stats.error_samples.append(message)