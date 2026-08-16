"""Sync actualités BDD → KnowledgeChunk (RAG assistant IA).

Exécuté après le scraping GitHub Actions — lecture depuis Convex (Phase 3)
ou Supabase (fallback), écriture KnowledgeChunk en SQL (inchangé).

Seuls les articles modifiés dans les dernières 25 h sont relus : sans ce
filtre, chaque run re-téléchargeait 250+ contenus complets depuis la BDD,
ce qui consumait l'egress du projet à chaque exécution.

Backend :
  • USE_CONVEX=1 (ou CONVEX_DEPLOY_KEY définie) → articles presse lus depuis
    Convex (getRecentArticlesWithContent) ; NewsArticle n'est PAS syncé (table
    vide côté Convex, documenté) ; l'écriture KnowledgeChunk reste en SQL sur
    DATABASE_URL (Aiven).
  • Sinon → comportement historique (Article + NewsArticle depuis Supabase).

Usage:
  python scripts/rag_sync_articles.py
  python scripts/rag_sync_articles.py --press-limit 250 --news-limit 40
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import uuid
from datetime import datetime, timezone

import psycopg2
from dotenv import load_dotenv
from psycopg2.extras import Json

import convex_client

_script_dir = os.path.dirname(os.path.abspath(__file__))
_root = os.path.dirname(_script_dir)
for _env in (".envenv", ".env.local", ".env"):
    load_dotenv(os.path.join(_root, _env))

DATABASE_URL = os.environ.get("DATABASE_URL", "").replace("?pgbouncer=true", "").replace("&pgbouncer=true", "")

# Backend : Convex (cloud) si USE_CONVEX=1 ou CONVEX_DEPLOY_KEY définie.
USE_CONVEX = convex_client.use_convex()
if USE_CONVEX:
    print("[*] Backend lecture articles presse: Convex (cloud)")
else:
    print("[*] Backend lecture articles presse: Supabase (psycopg2)")

MAX_CHUNK_CHARS = 3000
OVERLAP_CHARS = 200


def content_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def chunk_text(text: str) -> list[tuple[int, str]]:
    normalized = text.replace("\r\n", "\n").strip()
    if not normalized:
        return []

    if len(normalized) <= MAX_CHUNK_CHARS:
        return [(0, normalized)]

    paragraphs = [p.strip() for p in re.split(r"\n{2,}", normalized) if p.strip()]
    chunks: list[tuple[int, str]] = []
    buffer = ""
    chunk_index = 0

    def push_chunk(value: str) -> None:
        nonlocal chunk_index
        trimmed = value.strip()
        if not trimmed:
            return
        chunks.append((chunk_index, trimmed))
        chunk_index += 1

    for paragraph in paragraphs:
        candidate = f"{buffer}\n\n{paragraph}" if buffer else paragraph
        if len(candidate) <= MAX_CHUNK_CHARS:
            buffer = candidate
            continue

        if buffer:
            push_chunk(buffer)

        if len(paragraph) <= MAX_CHUNK_CHARS:
            buffer = paragraph
            continue

        start = 0
        while start < len(paragraph):
            end = min(start + MAX_CHUNK_CHARS, len(paragraph))
            push_chunk(paragraph[start:end])
            if end >= len(paragraph):
                break
            start = max(end - OVERLAP_CHARS, start + 1)
        buffer = ""

    if buffer:
        push_chunk(buffer)

    return chunks


def format_press_article(row: dict) -> str | None:
    pub = row.get("publishedAt")
    if USE_CONVEX and isinstance(pub, (int, float)):
        pub_str = datetime.fromtimestamp(pub / 1000, tz=timezone.utc).strftime("%Y-%m-%d")
    elif isinstance(pub, datetime):
        pub_str = pub.strftime("%Y-%m-%d")
    else:
        pub_str = ""
    parts = [
        f"Titre: {row['title']}",
        f"Source: {row['source']}" if row.get("source") else None,
        f"Résumé: {row['description']}" if row.get("description") else None,
        f"Contenu: {row['content']}" if row.get("content") else None,
        f"Publié le: {pub_str}" if pub_str else None,
    ]
    body = "\n".join(p for p in parts if p)
    return body if len(body) >= 40 else None


def format_news_article(row: dict) -> str:
    parts = [
        f"Article: {row['title']}",
        f"Résumé: {row['excerpt']}" if row.get("excerpt") else None,
        f"Contenu: {row['content']}",
        f"Publié le: {row['publishedAt'].strftime('%Y-%m-%d')}" if row.get("publishedAt") else None,
    ]
    return "\n".join(p for p in parts if p)


def ensure_fts_index(cur) -> None:
    cur.execute(
        """
        CREATE INDEX IF NOT EXISTS knowledge_chunk_fts_idx
        ON "KnowledgeChunk"
        USING gin (to_tsvector('french', coalesce(title, '') || ' ' || content))
        """
    )


def upsert_document(
    cur,
    *,
    source_type: str,
    source_id: str,
    title: str,
    content: str,
    url: str | None,
    metadata: dict | None,
    stats: dict,
) -> None:
    chunks = chunk_text(content)
    if not chunks:
        stats["skipped"] += 1
        return

    hashes = [
        content_hash(f"{source_type}:{source_id}:{idx}:{text}")
        for idx, text in chunks
    ]

    cur.execute(
        """
        SELECT "chunkIndex", "contentHash"
        FROM "KnowledgeChunk"
        WHERE "sourceType" = %s AND "sourceId" = %s
        """,
        (source_type, source_id),
    )
    existing = {row[0]: row[1] for row in cur.fetchall()}

    unchanged = len(chunks) == len(existing) and all(
        existing.get(idx) == h for (idx, _), h in zip(chunks, hashes)
    )
    if unchanged:
        stats["skipped"] += 1
        return

    cur.execute(
        'DELETE FROM "KnowledgeChunk" WHERE "sourceType" = %s AND "sourceId" = %s',
        (source_type, source_id),
    )

    now = datetime.now(timezone.utc)
    for (chunk_index, text), h in zip(chunks, hashes):
        cur.execute(
            """
            INSERT INTO "KnowledgeChunk"
              (id, "sourceType", "sourceId", title, content, url, metadata, "chunkIndex", "contentHash", "updatedAt")
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                str(uuid.uuid4()),
                source_type,
                source_id,
                title,
                text,
                url,
                Json(metadata) if metadata else None,
                chunk_index,
                h,
                now,
            ),
        )
        stats["indexed"] += 1
        stats["by_source"][source_type] = stats["by_source"].get(source_type, 0) + 1


def sync_press_articles(cur, limit: int, stats: dict) -> None:
    if USE_CONVEX:
        # Lecture Convex : articles récents hidden=false avec contenu (25h).
        # `id` = supabaseId (sourceId stable du RAG) ; le tri SQL par updatedAt
        # est approché par un scan borné côté Convex (voir scrapers.ts).
        rows = convex_client.get_recent_articles_with_content(limit=limit, hours=25)
        for article in rows:
            body = format_press_article(article)
            if not body:
                stats["skipped"] += 1
                continue
            try:
                upsert_document(
                    cur,
                    source_type="article",
                    source_id=article["id"],
                    title=article["title"],
                    content=body,
                    url=article["link"],
                    metadata={
                        "source": article["source"] or "",
                        "publishedAt": datetime.fromtimestamp(
                            article["publishedAt"] / 1000, tz=timezone.utc
                        ).isoformat(),
                    },
                    stats=stats,
                )
            except Exception as exc:
                stats["errors"] += 1
                print(f"  [ERR] article {article['id']}: {exc}", file=sys.stderr)
        return

    cur.execute(
        """
        SELECT id, title, description, content, source, link, "publishedAt"
        FROM "Article"
        WHERE hidden = false
          AND "updatedAt" > NOW() - INTERVAL '25 hours'
        ORDER BY "updatedAt" DESC
        LIMIT %s
        """,
        (limit,),
    )
    for row in cur.fetchall():
        article = {
            "id": row[0],
            "title": row[1],
            "description": row[2],
            "content": row[3],
            "source": row[4],
            "link": row[5],
            "publishedAt": row[6],
        }
        body = format_press_article(article)
        if not body:
            stats["skipped"] += 1
            continue
        try:
            upsert_document(
                cur,
                source_type="article",
                source_id=article["id"],
                title=article["title"],
                content=body,
                url=article["link"],
                metadata={
                    "source": article["source"] or "",
                    "publishedAt": article["publishedAt"].isoformat(),
                },
                stats=stats,
            )
        except Exception as exc:
            stats["errors"] += 1
            print(f"  [ERR] article {article['id']}: {exc}", file=sys.stderr)


def sync_news_articles(cur, limit: int, stats: dict, site_url: str) -> None:
    cur.execute(
        """
        SELECT id, title, slug, excerpt, content, "publishedAt"
        FROM "NewsArticle"
        WHERE hidden = false AND "statusWorkflow" = 'PUBLISHED'
          AND "updatedAt" > NOW() - INTERVAL '25 hours'
        ORDER BY "updatedAt" DESC
        LIMIT %s
        """,
        (limit,),
    )
    for row in cur.fetchall():
        article = {
            "id": row[0],
            "title": row[1],
            "slug": row[2],
            "excerpt": row[3],
            "content": row[4],
            "publishedAt": row[5],
        }
        body = format_news_article(article)
        url = f"{site_url.rstrip('/')}/actualites/{article['slug']}"
        try:
            upsert_document(
                cur,
                source_type="news_article",
                source_id=article["id"],
                title=article["title"],
                content=body,
                url=url,
                metadata={
                    "publishedAt": article["publishedAt"].isoformat() if article["publishedAt"] else "",
                },
                stats=stats,
            )
        except Exception as exc:
            stats["errors"] += 1
            print(f"  [ERR] news_article {article['id']}: {exc}", file=sys.stderr)


def main() -> int:
    parser = argparse.ArgumentParser(description="Sync actualités → RAG (KnowledgeChunk)")
    parser.add_argument("--press-limit", type=int, default=40)
    parser.add_argument("--news-limit", type=int, default=40)
    args = parser.parse_args()

    if not DATABASE_URL:
        print("DATABASE_URL manquant", file=sys.stderr)
        return 1

    site_url = os.environ.get("NEXT_PUBLIC_SITE_URL", "https://www.mulhouse68.fr")

    stats = {"indexed": 0, "skipped": 0, "errors": 0, "by_source": {}}

    conn = psycopg2.connect(DATABASE_URL)
    try:
        cur = conn.cursor()
        ensure_fts_index(cur)
        sync_press_articles(cur, args.press_limit, stats)
        if not USE_CONVEX:
            # En mode Convex, NewsArticle n'est pas syncé : la table est vide
            # côté Convex (documenté) et l'écriture Aiven reste en SQL.
            sync_news_articles(cur, args.news_limit, stats, site_url)
        conn.commit()
    finally:
        conn.close()

    print("--- Sync RAG actualités (GitHub Actions) ---")
    print(f"Chunks indexés : {stats['indexed']}")
    print(f"Ignorés (inchangés) : {stats['skipped']}")
    print(f"Erreurs : {stats['errors']}")
    if stats["by_source"]:
        print("Par source :", stats["by_source"])

    return 0 if stats["errors"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())