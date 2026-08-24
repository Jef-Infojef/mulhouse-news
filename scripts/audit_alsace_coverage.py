"""Compare sitemap L'Alsace (URL mulhouse + HTML 68224) vs Convex.

Usage (prod) :
  python scripts/audit_alsace_coverage.py --prod

Ne fait aucune écriture. Affiche le manque par jour + liste des URLs absentes.
"""
from __future__ import annotations

import argparse
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, datetime
from pathlib import Path

NEWS_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(NEWS_ROOT / "scripts"))

from dotenv import load_dotenv

for _env in (".envenv", ".env.local", ".env"):
    load_dotenv(NEWS_ROOT / _env)

import convex_client
from scrape_alsace_archive import fetch_sitemap, parse_sitemap
from scrape_utils import html_is_mulhouse_edition, is_mulhouse_url

# Jours types : semaine, pas un 1er janvier vide.
PRE_2020 = [
    "2012-03-14",
    "2013-11-09",  # Grand Rex (fil d'Ariane, pas le slug)
    "2016-06-15",
    "2019-03-20",
]
Y2026 = [
    "2026-01-20",
    "2026-04-08",
    "2026-07-15",
    "2026-08-10",
    "2026-08-22",
]

HTML_WORKERS = 10


def classify_day(day: str) -> dict:
    xml = fetch_sitemap(f"https://www.lalsace.fr/sitemap-{day}.xml")
    if not xml:
        return {
            "day": day,
            "error": "sitemap introuvable",
            "sitemap": 0,
            "by_url": [],
            "by_html": [],
            "html_scanned": 0,
            "html_errors": 0,
        }
    parsed = parse_sitemap(xml)
    by_url = [e["link"] for e in parsed if is_mulhouse_url(e["link"])]
    rest = [e["link"] for e in parsed if not is_mulhouse_url(e["link"])]
    by_html: list[str] = []
    html_errors = 0
    scanned = 0
    t0 = time.time()

    def check(url: str) -> tuple[str, bool | None]:
        html = fetch_sitemap(url)
        if not html:
            return url, None
        return url, html_is_mulhouse_edition(html)

    if rest:
        with ThreadPoolExecutor(max_workers=HTML_WORKERS) as pool:
            futs = [pool.submit(check, url) for url in rest]
            for fut in as_completed(futs):
                scanned += 1
                url, hit = fut.result()
                if hit is None:
                    html_errors += 1
                elif hit:
                    by_html.append(url)
                if scanned % 50 == 0 or scanned == len(rest):
                    elapsed = time.time() - t0
                    rate = scanned / elapsed if elapsed else 0
                    left = (len(rest) - scanned) / rate if rate else 0
                    print(
                        f"    [{day}] HTML {scanned}/{len(rest)} | "
                        f"68224+ {len(by_html)} | err {html_errors} | "
                        f"{rate:.1f}/s | reste ~{int(left)}s",
                        flush=True,
                    )

    return {
        "day": day,
        "error": None,
        "sitemap": len(parsed),
        "by_url": by_url,
        "by_html": by_html,
        "html_scanned": scanned,
        "html_errors": html_errors,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit couverture L'Alsace Mulhouse vs Convex")
    parser.add_argument("--prod", action="store_true", help="Convex prod (MulhouseGPT/.env.local)")
    parser.add_argument(
        "--dates",
        type=str,
        default="",
        help="Dates YYYY-MM-DD séparées par des virgules (défaut : échantillon)",
    )
    parser.add_argument("--pre-2020", action="store_true")
    parser.add_argument("--y2026", action="store_true")
    args = parser.parse_args()

    if args.prod:
        load_dotenv(r"C:\dev\MulhouseGPT\.env.local", override=True)
        # convex_client lit l'env à l'appel
        os.environ.setdefault("USE_CONVEX", "1")

    if not convex_client.use_convex():
        print("❌ Convex non configuré (CONVEX_DEPLOY_KEY + NEXT_PUBLIC_CONVEX_URL)")
        return 1
    print(f"[*] Convex : {convex_client.get_convex_url()}", flush=True)

    if args.dates:
        days = [d.strip() for d in args.dates.split(",") if d.strip()]
    elif args.pre_2020 and not args.y2026:
        days = PRE_2020
    elif args.y2026 and not args.pre_2020:
        days = Y2026
    else:
        days = PRE_2020 + Y2026

    for d in days:
        datetime.strptime(d, "%Y-%m-%d")

    print(f"[*] {len(days)} jour(s) : {', '.join(days)}", flush=True)
    rows = []
    missing_all: list[tuple[str, str, str]] = []

    for i, day in enumerate(days, 1):
        print(f"\n=== {i}/{len(days)} {day} ===", flush=True)
        info = classify_day(day)
        if info["error"]:
            print(f"    [!] {info['error']}", flush=True)
            rows.append(info)
            continue
        candidates = info["by_url"] + info["by_html"]
        existing = convex_client.get_existing_links_for(candidates) if candidates else set()
        missing = [u for u in candidates if u not in existing]
        info["in_db"] = len(candidates) - len(missing)
        info["missing"] = missing
        info["mulhouse"] = len(candidates)
        era = "pre-2020" if day < "2020-01-01" else "2026"
        print(
            f"    sitemap {info['sitemap']} | URL {len(info['by_url'])} | "
            f"HTML-68224 {len(info['by_html'])} | Mulhouse {info['mulhouse']} | "
            f"en base {info['in_db']} | MANQUE {len(missing)}",
            flush=True,
        )
        for url in missing:
            how = "url" if url in info["by_url"] else "68224"
            missing_all.append((era, day, url))
            print(f"      MANQUE [{how}] {url}", flush=True)
        rows.append(info)

    print("\n========== SYNTHÈSE ==========")
    print(f"{'jour':<12} {'era':<8} {'sm':>5} {'url':>4} {'html':>5} {'MH':>4} {'db':>4} {'manque':>6}")
    tot_m = tot_db = tot_miss = 0
    for info in rows:
        if info.get("error"):
            print(f"{info['day']:<12} ERR {info['error']}")
            continue
        era = "pre-2020" if info["day"] < "2020-01-01" else "2026"
        miss = len(info.get("missing") or [])
        mh = info.get("mulhouse") or 0
        db = info.get("in_db") or 0
        tot_m += mh
        tot_db += db
        tot_miss += miss
        print(
            f"{info['day']:<12} {era:<8} {info['sitemap']:>5} "
            f"{len(info['by_url']):>4} {len(info['by_html']):>5} {mh:>4} {db:>4} {miss:>6}"
        )
    print(f"{'TOTAL':<12} {'':<8} {'':>5} {'':>4} {'':>5} {tot_m:>4} {tot_db:>4} {tot_miss:>6}")
    if tot_m:
        print(f"Couverture : {100.0 * tot_db / tot_m:.1f}% des articles Mulhouse (URL + 68224)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
