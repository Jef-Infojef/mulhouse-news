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

_script_dir = os.path.dirname(os.path.abspath(__file__))
if _script_dir not in sys.path:
    sys.path.insert(0, _script_dir)

import convex_client

_root = os.path.dirname(_script_dir)
for _env in (".envenv", ".env.local", ".env"):
    load_dotenv(os.path.join(_root, _env))

# Fallback MulhouseGPT pour RAG_DATABASE_URL si non trouvé en local
if not os.environ.get("RAG_DATABASE_URL"):
    for _alt_path in ("C:/dev/MulhouseGPT/.env.local", "C:/dev/MulhouseGPT/.env", "../MulhouseGPT/.env.local"):
        if os.path.exists(_alt_path):
            load_dotenv(_alt_path)
            if os.environ.get("RAG_DATABASE_URL"):
                break

import urllib.parse

def _clean_url(v: str) -> str:
    if not v:
        return ""
    if "?" in v:
        base, query = v.split("?", 1)
        params = urllib.parse.parse_qs(query)
        clean_params = {}
        if "sslmode" in params:
            clean_params["sslmode"] = params["sslmode"][0]
        return base + ("?" + urllib.parse.urlencode(clean_params) if clean_params else "")
    return v

# Base RAG (KnowledgeChunk) : toujours Aiven (RAG_DATABASE_URL).
RAG_URL = _clean_url(os.environ.get("RAG_DATABASE_URL", "") or "")
# Source des articles en mode non-Convex : Supabase / PostgreSQL.
DATABASE_URL = _clean_url(os.environ.get("DATABASE_URL", "") or "")
NEWS_URL = _clean_url(
    os.environ.get("DATABASE_URL", "") or os.environ.get("NEWS_DATABASE_URL", "") or ""
)

# Backend : Convex si activé et configuré, avec fallback automatique PostgreSQL.
USE_CONVEX_ENV = os.environ.get("USE_CONVEX", "1").strip().lower()
USE_CONVEX = convex_client.use_convex() if USE_CONVEX_ENV not in ("0", "false", "no") else False


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


def press_metadata(source: str | None, published_at: str, image_url: str | None) -> dict:
    """Metadonnees d'un article presse pour le RAG.

    `imageUrl` illustre la carte de source cote MulhouseGPT ; l'omettre laissait
    les articles recents sans photo alors que l'image existait dans Convex.
    Cle absente plutot que vide : le lecteur teste la presence.
    """
    meta = {"source": source or "", "publishedAt": published_at}
    if image_url:
        meta["imageUrl"] = image_url
    return meta


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
        # L'empreinte ne couvre que le texte : une metadonnee arrivee APRES la
        # premiere indexation (illustration rattachee quelques minutes plus tard)
        # n'entrait jamais dans l'index, et l'article restait sans photo sous
        # les sources. On rafraichit title/url/metadata sans reinserer.
        meta_json = Json(metadata) if metadata else None
        cur.execute(
            """
            UPDATE "KnowledgeChunk"
               SET metadata = %s, title = %s, url = %s
             WHERE "sourceType" = %s AND "sourceId" = %s
               AND (metadata IS DISTINCT FROM %s OR title IS DISTINCT FROM %s
                    OR url IS DISTINCT FROM %s)
            """,
            (meta_json, title, url, source_type, source_id, meta_json, title, url),
        )
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


def sync_press_articles(rag_cur, news_cur, limit: int, stats: dict, full: bool = False, use_convex_mode: bool = False) -> None:
    if use_convex_mode:
        try:
            if full:
                print("[*] Mode FULL Convex : indexation de tous les articles avec contenu...")
                rows = convex_client.get_all_articles_with_content(limit=limit)
            else:
                rows = convex_client.get_recent_articles_with_content(limit=limit, hours=25)
            for article in rows:
                body = format_press_article(article)
                if not body:
                    stats["skipped"] += 1
                    continue
                try:
                    upsert_document(
                        rag_cur,
                        source_type="article",
                        source_id=article["id"],
                        title=article["title"],
                        content=body,
                        url=article["link"],
                        metadata=press_metadata(
                            article["source"],
                            datetime.fromtimestamp(
                                article["publishedAt"] / 1000, tz=timezone.utc
                            ).isoformat(),
                            article.get("imageUrl") or article.get("r2Url"),
                        ),
                        stats=stats,
                    )
                except Exception as exc:
                    stats["errors"] += 1
                    print(f"  [ERR] article {article['id']}: {exc}", file=sys.stderr)
            return
        except Exception as exc:
            print(f"[!] Convex indisponible ({exc}) -> bascule automatique sur PostgreSQL.", file=sys.stderr)
            if not news_cur:
                raise

    where_clause = """
        WHERE hidden = false 
          AND (
            ("content" IS NOT NULL AND length("content") >= 40)
            OR ("description" IS NOT NULL AND length("description") >= 20)
          )
    """
    if not full:
        where_clause += " AND \"updatedAt\" > NOW() - INTERVAL '25 hours'"

    sql = f"""
        SELECT id, title, description, content, source, link, "publishedAt"
        FROM "Article"
        {where_clause}
        ORDER BY "publishedAt" DESC
        LIMIT %s
    """
    news_cur.execute(sql, (limit,))
    for row in news_cur.fetchall():
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
                rag_cur,
                source_type="article",
                source_id=article["id"],
                title=article["title"],
                content=body,
                url=article["link"],
                metadata=press_metadata(
                    article["source"],
                    article["publishedAt"].isoformat() if article["publishedAt"] else "",
                    article.get("imageUrl"),
                ),
                stats=stats,
            )
        except Exception as exc:
            stats["errors"] += 1
            print(f"  [ERR] article {article['id']}: {exc}", file=sys.stderr)


def sync_news_articles(rag_cur, news_cur, limit: int, stats: dict, site_url: str, full: bool = False) -> None:
    if not news_cur:
        return
    where_clause = "WHERE hidden = false AND \"statusWorkflow\" = 'PUBLISHED'"
    if not full:
        where_clause += " AND \"updatedAt\" > NOW() - INTERVAL '25 hours'"

    sql = f"""
        SELECT id, title, slug, excerpt, content, "publishedAt"
        FROM "NewsArticle"
        {where_clause}
        ORDER BY "publishedAt" DESC
        LIMIT %s
    """
    news_cur.execute(sql, (limit,))
    for row in news_cur.fetchall():
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
                rag_cur,
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
    parser.add_argument("--press-limit", type=int, default=100)
    parser.add_argument("--news-limit", type=int, default=40)
    parser.add_argument("--full", action="store_true",
                        help="Backfill complet : indexe tous les articles avec contenu (ignore la borne 25h)")
    parser.add_argument("--postgres", action="store_true", help="Force la lecture PostgreSQL directe")
    args = parser.parse_args()

    if not RAG_URL:
        print("RAG_DATABASE_URL manquant (cible d'écriture KnowledgeChunk)", file=sys.stderr)
        return 1

    site_url = os.environ.get("NEXT_PUBLIC_SITE_URL", "https://www.mulhouse68.fr")

    stats = {"indexed": 0, "skipped": 0, "errors": 0, "by_source": {}}

    use_convex = USE_CONVEX and not args.postgres
    if use_convex:
        print("[*] Backend lecture initial : Convex (cloud)")
    else:
        print("[*] Backend lecture : PostgreSQL / Supabase")

    # Écriture des vecteurs : TOUJOURS Aiven (RAG_DATABASE_URL).
    rag_conn = psycopg2.connect(RAG_URL)
    # Connexion de lecture PostgreSQL toujours préparée au besoin (pour newsArticles ou fallback)
    news_conn = psycopg2.connect(NEWS_URL) if NEWS_URL else None

    try:
        rag_cur = rag_conn.cursor()
        ensure_fts_index(rag_cur)
        news_cur = news_conn.cursor() if news_conn else None
        sync_press_articles(rag_cur, news_cur, args.press_limit, stats, full=args.full, use_convex_mode=use_convex)
        if news_cur:
            sync_news_articles(rag_cur, news_cur, args.news_limit, stats, site_url, full=args.full)
        rag_conn.commit()
        if news_conn:
            news_conn.commit()
    finally:
        rag_conn.close()
        if news_conn:
            news_conn.close()

    print("--- Sync RAG actualités (GitHub Actions) ---")
    print(f"Chunks indexés : {stats['indexed']}")
    print(f"Ignorés (inchangés) : {stats['skipped']}")
    print(f"Erreurs : {stats['errors']}")
    if stats["by_source"]:
        print("Par source :", stats["by_source"])

    return 0 if stats["errors"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())