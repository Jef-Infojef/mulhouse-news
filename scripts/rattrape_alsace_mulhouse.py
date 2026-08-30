"""Rattrapage L'Alsace Mulhouse, article par article (découverte //, RAG process unique).

  python scripts/rattrape_alsace_mulhouse.py --start 2013-01-01 --end 2013-12-31
"""

from __future__ import annotations

import argparse
import html
import os
import re
import shutil
import subprocess
import sys
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
NEWS_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(NEWS_ROOT / "scripts"))

from dotenv import load_dotenv

for _env in (".envenv", ".env.local", ".env"):
    load_dotenv(NEWS_ROOT / _env)

import convex_client
from curl_cffi import requests as curl_requests
from scrape_alsace_archive import (
    SOURCE,
    fetch_sitemap,
    list_daily_sitemaps,
    parse_sitemap,
)
from scrape_content_full import fetch_article_content, load_ebra_cookies
from scrape_utils import html_is_mulhouse_edition, is_mulhouse_url

DEFAULT_GPT = Path(os.environ.get("MULHOUSEGPT_DIR", NEWS_ROOT.parent / "MulhouseGPT"))
MIN_CONTENT = 150
SITEMAP_WORKERS = 12
HTML_WORKERS = 12
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"

OG_TITLE_RES = [
    re.compile(r'<meta[^>]+property=["\']og:title["\'][^>]+content=["\'](.*?)["\']', re.I | re.S),
    re.compile(r'<meta[^>]+content=["\'](.*?)["\'][^>]+property=["\']og:title["\']', re.I | re.S),
]
OG_IMAGE_RES = [
    re.compile(r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\'](https?://[^"\']+?)["\']', re.I | re.S),
    re.compile(r'<meta[^>]+content=["\'](https?://[^"\']+?)["\'][^>]+property=["\']og:image["\']', re.I | re.S),
]
CDN_LALSACE = re.compile(r"^https://cdn-s-www\.lalsace\.fr/images/", re.I)


def fetch_page_meta(url: str) -> tuple[str | None, str | None]:
    """(og:title, og:image) de la page — le titre du sitemap n'est qu'un slug
    sans accents, et l'image n'est jamais capturée par l'insert d'archive."""
    try:
        resp = curl_requests.get(url, timeout=30, impersonate="chrome120", headers={"User-Agent": UA})
        if resp.status_code != 200:
            return None, None

        def find(regexes: list[re.Pattern]) -> str | None:
            m = next((m for m in (r.search(resp.text) for r in regexes) if m), None)
            return html.unescape(m.group(1)).strip() if m else None

        title = find(OG_TITLE_RES)
        image = find(OG_IMAGE_RES)
        if image and not CDN_LALSACE.match(image):
            image = None
        return (title or None), image
    except Exception:  # noqa: BLE001 — best effort, ne doit pas casser le run
        return None, None


def parse_day(value: str) -> str:
    try:
        datetime.strptime(value, "%Y-%m-%d")
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"date YYYY-MM-DD attendue, reçu {value!r}") from exc
    return value


def link_variants(url: str) -> list[str]:
    out = [url]
    swapped = url.replace("://c.lalsace.fr", "://www.lalsace.fr")
    if swapped == url:
        swapped = url.replace("://www.lalsace.fr", "://c.lalsace.fr")
    if swapped != url:
        out.append(swapped)
    return out


class RagWorker:
    """Un seul process Node : évite npx/tsx/dotenv à chaque article."""

    def __init__(self, gpt_dir: Path):
        self.gpt_dir = gpt_dir
        self.proc: subprocess.Popen[str] | None = None
        self._start()

    def _start(self) -> None:
        node = shutil.which("node")
        if not node:
            raise RuntimeError("node introuvable")
        env = os.environ.copy()
        env["DOTENV_CONFIG_QUIET"] = "true"
        env["npm_config_loglevel"] = "silent"
        env["npm_config_update_notifier"] = "false"
        self.proc = subprocess.Popen(
            [node, "--import", "tsx", "scripts/rag-index-article.ts", "--worker"],
            cwd=str(self.gpt_dir),
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            bufsize=1,
            env=env,
        )
        assert self.proc.stdout
        ready = self.proc.stdout.readline()
        if "READY" not in (ready or ""):
            raise RuntimeError(f"worker RAG muet ({ready!r})")
        print("[*] Worker RAG prêt", flush=True)

    def index(self, source_id: str, timeout: float = 90) -> bool:
        if not self.proc or self.proc.poll() is not None:
            self._start()
        assert self.proc and self.proc.stdin and self.proc.stdout
        self.proc.stdin.write(source_id + "\n")
        self.proc.stdin.flush()
        deadline = time.time() + timeout
        while time.time() < deadline:
            line = self.proc.stdout.readline()
            if not line:
                return False
            line = line.strip()
            if line.startswith("OK"):
                print(f"      RAG {line}", flush=True)
                return True
            if line.startswith("ERR"):
                print(f"      ❌ RAG {line}", flush=True)
                return False
        print("      ❌ RAG timeout", flush=True)
        return False

    def close(self) -> None:
        if not self.proc:
            return
        try:
            if self.proc.stdin and self.proc.poll() is None:
                self.proc.stdin.write("QUIT\n")
                self.proc.stdin.flush()
            self.proc.wait(timeout=8)
        except Exception:
            self.proc.kill()
        self.proc = None


def load_rag_urls(rag_cur) -> set[str]:
    if not rag_cur:
        return set()
    print("[*] Chargement des URLs déjà vectorisées…", flush=True)
    rag_cur.execute(
        """
        SELECT DISTINCT url FROM "KnowledgeChunk"
        WHERE "sourceType" = 'article' AND embedding IS NOT NULL AND url IS NOT NULL
        """
    )
    urls = {row[0] for row in rag_cur.fetchall() if row[0]}
    print(f"[*] {len(urls)} URL déjà dans le RAG", flush=True)
    return urls


def already_in_rag(url: str, rag_urls: set[str]) -> bool:
    return any(v in rag_urls for v in link_variants(url))


def lookup_convex(url: str) -> dict | None:
    for link in link_variants(url):
        doc = convex_client.get_article_by_link(link)
        if doc:
            return doc
    return None


def content_len(doc: dict | None) -> int:
    if not doc:
        return 0
    return len(doc.get("content") or "")


def published_ms(entry: dict) -> int | None:
    pub = entry.get("publishedAt")
    if not pub:
        return None
    if hasattr(pub, "timestamp"):
        return int(pub.timestamp() * 1000)
    return None


def process_one(
    entry: dict,
    *,
    cookies: dict,
    cookies_ok: bool,
    rag_urls: set[str],
    worker: RagWorker | None,
    skip_rag: bool,
    dry_run: bool,
    stats: dict,
) -> None:
    url = entry["link"]
    title = entry.get("title") or url.rsplit("/", 1)[-1]

    if already_in_rag(url, rag_urls):
        print(f"  skip  déjà RAG  {title[:70]}", flush=True)
        stats["skip"] += 1
        return

    existing = lookup_convex(url)
    supabase_id = (existing or {}).get("supabaseId")
    full = convex_client.get_article_by_supabase_id(supabase_id) if supabase_id else None
    complete = content_len(full) >= MIN_CONTENT

    if existing and complete:
        print(f"  rag   texte ok, pas encore vectorisé  {title[:70]}", flush=True)
        stats["rag_only"] += 1
        if dry_run or skip_rag or not supabase_id or not worker:
            return
        if worker.index(supabase_id):
            for v in link_variants(url):
                rag_urls.add(v)
            stats["rag_ok"] += 1
        else:
            stats["errors"] += 1
        return

    if dry_run:
        print(f"  dry   {'créerait' if not existing else 'compléterait'}  {title[:70]}", flush=True)
        stats["todo"] += 1
        return

    # Vrai titre (accents) + photo : le titre de sitemap n'est qu'un slug.
    og_title, og_image = fetch_page_meta(url)
    if og_title:
        title = og_title

    used_link = (existing or {}).get("link") or url
    if not existing:
        supabase_id = str(uuid.uuid4())
        upsert: dict = {
            "title": title,
            "link": url,
            "source": SOURCE,
            "publishedAt": published_ms(entry),
            "updatedAt": int(time.time() * 1000),
            "supabaseId": supabase_id,
        }
        if og_image:
            upsert["imageUrl"] = og_image
        convex_client.upsert_article(upsert)
        print(f"  new   {title[:70]}", flush=True)
        stats["created"] += 1
    else:
        print(f"  fill  texte court ({content_len(full)} car.)  {title[:70]}", flush=True)
        stats["filled"] += 1
        fill_upsert: dict = {"link": used_link, "title": title, "updatedAt": int(time.time() * 1000)}
        if og_image:
            fill_upsert["imageUrl"] = og_image
        if not supabase_id:
            supabase_id = str(uuid.uuid4())
            fill_upsert["supabaseId"] = supabase_id
        convex_client.upsert_article(fill_upsert)

    content, _caption, _active, err, _images = fetch_article_content(used_link, cookies, cookies_ok)
    if not content or len(content) < MIN_CONTENT:
        print(f"      ❌ GRDC {err or 'texte trop court'}", flush=True)
        stats["errors"] += 1
        return

    convex_client.upsert_article(
        {
            "link": used_link,
            "content": content,
            "title": title,
            **({"imageUrl": og_image} if og_image else {}),
            "updatedAt": int(time.time() * 1000),
        }
    )
    print(f"      GRDC {len(content)} car.", flush=True)

    if skip_rag or not worker or not supabase_id:
        return
    if worker.index(supabase_id):
        for v in link_variants(url):
            rag_urls.add(v)
        stats["rag_ok"] += 1
    else:
        stats["errors"] += 1


def classify_entries(entries: list[dict], label: str = "") -> list[dict]:
    """Slug Mulhouse tout de suite ; les autres : GET HTML en parallèle."""
    keep: list[dict] = []
    need_html: list[dict] = []
    for entry in entries:
        if is_mulhouse_url(entry["link"]):
            keep.append(entry)
        else:
            need_html.append(entry)
    if not need_html:
        return keep

    def check(entry: dict) -> dict | None:
        html = fetch_sitemap(entry["link"])
        if html and html_is_mulhouse_edition(html):
            return entry
        return None

    done = 0
    hits = 0
    t0 = time.time()
    prefix = f"    [{label}] " if label else "    "
    with ThreadPoolExecutor(max_workers=HTML_WORKERS) as pool:
        futures = [pool.submit(check, e) for e in need_html]
        for fut in as_completed(futures):
            hit = fut.result()
            done += 1
            if hit:
                hits += 1
                keep.append(hit)
            if done % 50 == 0 or done == len(need_html):
                elapsed = time.time() - t0
                rate = done / elapsed if elapsed else 0
                left = (len(need_html) - done) / rate if rate else 0
                print(
                    f"{prefix}HTML {done}/{len(need_html)} | 68224+ {hits} | "
                    f"{rate:.1f}/s | reste ~{int(left)}s",
                    flush=True,
                )
    return keep


def main() -> None:
    parser = argparse.ArgumentParser(description="Rattrapage L'Alsace 1 à 1 (Convex + GRDC + RAG).")
    parser.add_argument("--prod", action="store_true", help="Convex prod (MulhouseGPT/.env.local)")
    parser.add_argument("--start", type=parse_day, required=True)
    parser.add_argument("--end", type=parse_day, default=None)
    parser.add_argument("--gpt-dir", type=Path, default=DEFAULT_GPT)
    parser.add_argument("--skip-rag", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--limit", type=int, default=0, help="Max d'articles traités (0 = tous)")
    args = parser.parse_args()
    end = args.end or args.start
    gpt = args.gpt_dir.resolve()
    start = datetime.strptime(args.start, "%Y-%m-%d").date()
    end_d = datetime.strptime(end, "%Y-%m-%d").date()

    if args.prod or (gpt / ".env.local").exists():
        load_dotenv(gpt / ".env.local", override=True)
        load_dotenv(gpt / ".env", override=True)
        os.environ.setdefault("USE_CONVEX", "1")
    else:
        load_dotenv(gpt / ".env.local")
        load_dotenv(gpt / ".env")

    rag_conn = rag_cur = None
    rag_url = (os.environ.get("RAG_DATABASE_URL") or os.environ.get("NEWS_DATABASE_URL") or "").replace(
        "?pgbouncer=true", ""
    )
    if rag_url and not args.dry_run:
        try:
            import psycopg2

            rag_conn = psycopg2.connect(rag_url.replace("&pgbouncer=true", ""))
            rag_cur = rag_conn.cursor()
        except Exception as exc:
            print(f"[!] RAG Postgres indisponible ({exc})", flush=True)

    if not convex_client.use_convex():
        print("❌ CONVEX_DEPLOY_KEY et NEXT_PUBLIC_CONVEX_URL sont requis.", file=sys.stderr)
        sys.exit(1)

    cookies, cookies_ok = load_ebra_cookies()
    rag_urls = load_rag_urls(rag_cur)
    worker = None if args.skip_rag or args.dry_run else RagWorker(gpt)

    print(
        f"Rattrapage 1-à-1  {args.start} → {end}\n"
        f"  session EBRA : {'oui' if cookies_ok else 'non'}\n"
        f"  gpt : {gpt}",
        flush=True,
    )

    sitemap_urls = list_daily_sitemaps(start, end_d)
    n_days = len(sitemap_urls)
    # ~12 s de HTML/jour (170–400 URL) + GRDC sur les manques : ordre de grandeur.
    print(
        f"[*] {n_days} jour(s) — HTML 68224 puis insert/GRDC/RAG des manques. "
        f"Durée typique ~{max(n_days * 15 // 60, 1)}–{max(n_days * 25 // 60, 2)} min "
        f"(filet URL déjà en base = skip).",
        flush=True,
    )
    print(f"[*] Téléchargement de {n_days} sitemaps ({SITEMAP_WORKERS} //)…", flush=True)
    xml_by_url: dict[str, str | None] = {}
    with ThreadPoolExecutor(max_workers=SITEMAP_WORKERS) as pool:
        futs = {pool.submit(fetch_sitemap, u): u for u in sitemap_urls}
        done = 0
        for fut in as_completed(futs):
            sm = futs[fut]
            xml_by_url[sm] = fut.result()
            done += 1
            if done % 100 == 0 or done == len(sitemap_urls):
                print(f"[*] sitemaps {done}/{len(sitemap_urls)}", flush=True)

    stats = {
        "seen": 0,
        "not_mulhouse": 0,
        "skip": 0,
        "rag_only": 0,
        "created": 0,
        "filled": 0,
        "rag_ok": 0,
        "todo": 0,
        "errors": 0,
    }
    processed = 0
    t0 = time.time()

    try:
        for i, sm_url in enumerate(sitemap_urls, 1):
            xml = xml_by_url.get(sm_url)
            if not xml:
                print(f"[{i}/{len(sitemap_urls)}] {sm_url.split('/')[-1]} : illisible", flush=True)
                continue
            entries = parse_sitemap(xml)
            day_label = sm_url.split("/")[-1].replace("sitemap-", "").replace(".xml", "")
            keep = classify_entries(entries, label=day_label)
            stats["not_mulhouse"] += len(entries) - len(keep)
            elapsed = time.time() - t0
            eta = (elapsed / i) * (len(sitemap_urls) - i) if i else 0
            print(
                f"[{i}/{len(sitemap_urls)}] {sm_url.split('/')[-1]} : "
                f"{len(entries)} URL → {len(keep)} Mulhouse | "
                f"{int(elapsed // 60):02d}m{int(elapsed % 60):02d}s | "
                f"ETA {int(eta // 60):02d}m{int(eta % 60):02d}s | "
                f"créés {stats['created']} err {stats['errors']}",
                flush=True,
            )
            for entry in keep:
                stats["seen"] += 1
                if args.limit and processed >= args.limit:
                    print(f"[*] Limite --limit {args.limit} atteinte.", flush=True)
                    raise StopIteration
                processed += 1
                try:
                    process_one(
                        entry,
                        cookies=cookies,
                        cookies_ok=cookies_ok,
                        rag_urls=rag_urls,
                        worker=worker,
                        skip_rag=args.skip_rag,
                        dry_run=args.dry_run,
                        stats=stats,
                    )
                except Exception as exc:
                    stats["errors"] += 1
                    print(f"      ❌ {exc}", flush=True)
    except StopIteration:
        pass
    finally:
        if worker:
            worker.close()
        if rag_conn:
            rag_conn.close()

    elapsed = time.time() - t0
    minutes, seconds = divmod(int(elapsed), 60)
    print(
        f"\n✅ {minutes} min {seconds} s — vus {stats['seen']} Mulhouse | "
        f"skip {stats['skip']} | rag-seul {stats['rag_only']} | "
        f"créés {stats['created']} | complétés {stats['filled']} | "
        f"RAG {stats['rag_ok']} | erreurs {stats['errors']} | hors sujet {stats['not_mulhouse']}",
        flush=True,
    )


if __name__ == "__main__":
    main()
