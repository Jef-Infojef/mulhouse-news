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


def normaliser_date(valeur) -> datetime | None:
    """Date de parution, quelle que soit la forme sous laquelle elle arrive.

    Le journal JSONL serialise les datetime en epoch ms (_json_default), mais un
    scraper qui pose deja une chaine ISO dans `publishedAt` la voit traverser
    telle quelle : elle n'etait alors ni int ni datetime, et la date partait a
    la poubelle sans un mot.
    """
    if isinstance(valeur, datetime):
        return valeur if valeur.tzinfo else valeur.replace(tzinfo=timezone.utc)
    if isinstance(valeur, (int, float)):
        return datetime.fromtimestamp(valeur / 1000, tz=timezone.utc)
    if isinstance(valeur, str) and valeur.strip():
        texte = valeur.strip()
        try:
            # fromisoformat ne lit le Z qu'a partir de Python 3.11.
            parsee = datetime.fromisoformat(texte.replace("Z", "+00:00"))
            return parsee if parsee.tzinfo else parsee.replace(tzinfo=timezone.utc)
        except ValueError:
            return None
    return None


def format_press_article(row: dict) -> str | None:
    # Une seule lecture de date pour tout le pont : le decodage local qui
    # n'acceptait les epoch ms que sous USE_CONVEX laissait passer des articles
    # sans la ligne « Publié le: », donc introuvables par une recherche datee.
    pub = normaliser_date(row.get("publishedAt"))
    pub_str = pub.strftime("%Y-%m-%d") if pub else ""
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


# `ensure_fts_index` a ete retiree le 2026-09-16, avec l'index qu'elle creait.
#
# `knowledge_chunk_fts_idx` etait un index d'expression sur
# to_tsvector('french', title || content), d'avant la colonne `search_vector` et
# sa configuration insensible aux accents. Plus aucune requete ne l'utilisait :
# 216 Mo pour 0 lecture et 0 tuple lu depuis la creation des statistiques, sur
# une instance dont le cache fait 190 Mo. Chaque INSERT et chaque UPDATE de la
# table recalculait pourtant son tsvector et l'inserait dans ce GIN, en pure
# perte — et l'autovacuum devait le parcourir avec le reste.
#
# Le CREATE INDEX IF NOT EXISTS le ressuscitait a chaque run, ce qui est
# precisement pourquoi il avait survecu a sa suppression. Ne pas le remettre :
# le plein texte passe par `search_vector` et
# `knowledge_chunk_fts_vector_idx` (237 Mo, 75 lectures, activement utilise).


def press_metadata(
    source: str | None,
    published_at: str,
    image_url: str | None,
    image_caption: str | None = None,
) -> dict:
    """Metadonnees d'un article presse pour le RAG.

    `imageUrl` illustre la carte de source cote MulhouseGPT ; l'omettre laissait
    les articles recents sans photo alors que l'image existait dans Convex.
    Cle absente plutot que vide : le lecteur teste la presence.

    Une chaine vide n'est PAS une absence pour le lecteur : `new Date("")` rend
    un NaN, que fetchRecentIndexedNews traite comme une date illisible et qui
    fait disparaitre l'article du fil d'actualite sans le moindre message. 43
    articles — dont toute la presse du 12/09/2026 — y ont ete perdus. On omet
    donc la cle plutot que d'y mettre du vide, comme le dit le paragraphe
    ci-dessus : le code ne le faisait pas.
    """
    meta = {}
    if source:
        meta["source"] = source
    if published_at:
        meta["publishedAt"] = published_at
    if image_url:
        meta["imageUrl"] = image_url
    # La legende accompagne la photo sous la carte de source (ask.ts la lit dans
    # `metadata->>'imageCaption'`). Meme regle que le reste : cle absente plutot
    # que vide. Le pont TypeScript (MulhouseGPT, formatters.ts) ecrit exactement
    # les memes cles — sans quoi chaque synchro deferait le travail de l'autre,
    # reecrivant des chunks pour rien sur une table ou tout UPDATE coute dix
    # index.
    if image_caption:
        meta["imageCaption"] = image_caption
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


def surrogate_source_id(link: str) -> str:
    """`sourceId` de secours, derive du lien, quand l'id Convex est inconnu.

    KnowledgeChunk deduplique sur (sourceType, sourceId) et n'a AUCUN index sur
    url : la reconciliation doit donc passer par une cle calculable, jamais par
    une recherche sur l'URL, sous peine de scanner une table de 446 Mo par
    article. Prefixe explicite pour qu'un tel document se reconnaisse.
    """
    return "link:" + hashlib.sha1(link.encode("utf-8")).hexdigest()


def store_article(cur, source_id: str, lien: str, article: dict, publie) -> None:
    """Ecrit la FICHE de l'article dans la table Article de l'Aiven.

    KnowledgeChunk ne porte que le texte : ni hidden, ni auteur, ni categorie,
    ni legende. Ces colonnes n'existaient que dans Convex jusqu'au chargement du
    13/09/2026 ; sans cette ecriture, la table se figerait a cette date.

    COALESCE sur la mise a jour : une entree de decouverte, sans contenu ni
    image, ne doit pas effacer ce qu'un passage precedent avait rempli.
    """
    cur.execute(
        """
        INSERT INTO "Article" (id, link, title, source, description, content, author,
                               category, hidden, "imageUrl", "imageCaption", "localImage",
                               "r2Url", "publishedAt", "scrapedAt", "updatedAt")
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, now(), now())
        ON CONFLICT (id) DO UPDATE SET
            link = EXCLUDED.link,
            title = COALESCE(EXCLUDED.title, "Article".title),
            source = COALESCE(EXCLUDED.source, "Article".source),
            description = COALESCE(EXCLUDED.description, "Article".description),
            content = COALESCE(EXCLUDED.content, "Article".content),
            author = COALESCE(EXCLUDED.author, "Article".author),
            category = COALESCE(EXCLUDED.category, "Article".category),
            hidden = EXCLUDED.hidden,
            "imageUrl" = COALESCE(EXCLUDED."imageUrl", "Article"."imageUrl"),
            "imageCaption" = COALESCE(EXCLUDED."imageCaption", "Article"."imageCaption"),
            "localImage" = COALESCE(EXCLUDED."localImage", "Article"."localImage"),
            "r2Url" = COALESCE(EXCLUDED."r2Url", "Article"."r2Url"),
            "publishedAt" = COALESCE(EXCLUDED."publishedAt", "Article"."publishedAt"),
            "updatedAt" = now()
        """,
        (
            source_id, lien, article.get("title") or "", article.get("source"),
            article.get("description"), article.get("content"), article.get("author"),
            article.get("category"), bool(article.get("hidden")), article.get("imageUrl"),
            article.get("imageCaption"), article.get("localImage"), article.get("r2Url"),
            publie,
        ),
    )


def store_article_partiel(cur, lien: str, article: dict) -> None:
    """Enrichit une fiche existante sans l'indexer.

    Le scraper de contenu consigne des entrees partielles — `{link,
    imageCaption}` par exemple — qui ne portent ni titre ni texte : elles n'ont
    rien a dire a l'index, mais completent la fiche. Pas d'INSERT : une fiche
    sans titre n'aurait aucun sens, et Article.title est NOT NULL.
    """
    champs = {
        "description": article.get("description"),
        "imageUrl": article.get("imageUrl"),
        "imageCaption": article.get("imageCaption"),
        "localImage": article.get("localImage"),
        "r2Url": article.get("r2Url"),
        "author": article.get("author"),
        "category": article.get("category"),
    }
    presents = {k: v for k, v in champs.items() if v}
    if not presents:
        return
    sets = ", ".join(f'"{k}" = COALESCE(%s, "Article"."{k}")' for k in presents)
    cur.execute(
        f'UPDATE "Article" SET {sets}, "updatedAt" = now() WHERE link = %s',
        (*presents.values(), lien),
    )


def store_image(cur, entree: dict) -> None:
    """Une image d'article. L'id Convex est inconnu hors ligne : cle derivee de
    (articleId, url), ce que Convex deduplique aussi."""
    article_id = entree.get("articleId")
    url = entree.get("url")
    if not article_id or not url:
        return
    cle = hashlib.sha1(f"{article_id}|{url}".encode("utf-8")).hexdigest()
    cur.execute(
        """
        INSERT INTO "ArticleImage" (id, "articleId", url, caption, source, position, "createdAt")
        VALUES (%s, %s, %s, %s, %s, %s, now())
        ON CONFLICT (id) DO UPDATE SET
            caption = COALESCE(EXCLUDED.caption, "ArticleImage".caption),
            source = COALESCE(EXCLUDED.source, "ArticleImage".source),
            position = COALESCE(EXCLUDED.position, "ArticleImage".position)
        """,
        (cle, article_id, url, entree.get("caption"), entree.get("source"), entree.get("position")),
    )


def store_tag(cur, entree: dict) -> None:
    cur.execute(
        'INSERT INTO "ArticleTag" ("articleId", "tagId") VALUES (%s, %s) ON CONFLICT DO NOTHING',
        (entree["articleId"], entree["tagId"]),
    )


def purge_articles_masques(rag_cur) -> int:
    """Retire de l'index les articles passes en `hidden` APRES leur indexation.

    Aucun chemin n'indexe un article masque — ni le journal, ni la lecture
    Convex, ni le repli SQL. Mais rien ne le retirait quand il le devenait
    ensuite : constate le 13/09/2026, 61 articles masques cote site, dont 46
    que le chat continuait de servir.

    Le texte n'est pas perdu : la table Article le conserve, un article
    re-publie sera reindexe au prochain passage qui le touche.
    """
    rag_cur.execute(
        """
        DELETE FROM "KnowledgeChunk" k
        USING "Article" a
        WHERE a.id = k."sourceId" AND a.hidden AND k."sourceType" = 'article'
        """
    )
    return rag_cur.rowcount or 0


def rafraichir_metadonnees(rag_cur, source_ids: list[str], stats: dict) -> None:
    """Recolle les metadonnees des chunks sur ce que porte la table Article.

    Le journal est ecrit AU FIL du scraping : quand un article y est consigne,
    son illustration n'est pas encore connue — elle arrive quelques minutes plus
    tard, par l'etape « Full Content & Image Scraper », et atterrit dans Article
    / ArticleImage. Le chunk, lui, etait deja ecrit sans `imageUrl`.

    Le rafraichissement de upsert_document ne pouvait pas rattraper ce cas : il
    ne s'applique qu'a un document qu'on lui represente, et un article deja
    indexe ne reapparait pas dans le journal. Seule la synchro quotidienne
    (MulhouseGPT, syncArticlesToRag) le faisait — et elle etait en echec sur
    Convex depuis le 12/09/2026. Resultat : les articles du jour, les plus
    servis, etaient justement ceux qui s'affichaient sans photo.

    On relit donc la table a la fin du run, une fois les annexes ecrites, et on
    remet a jour ce qui a change. `IS DISTINCT FROM` sur le jsonb compare cote
    SQL, independamment de l'ordre des cles : un chunk deja correct n'est pas
    reecrit, ce qui compte sur une table ou chaque UPDATE touche dix index.
    """
    if not source_ids:
        return
    rag_cur.execute(
        """
        SELECT id, title, link, source, "publishedAt",
               coalesce(NULLIF("imageUrl", ''), NULLIF("r2Url", '')) AS "imageUrl",
               "imageCaption"
          FROM "Article" WHERE id = ANY(%s)
        """,
        (source_ids,),
    )
    recolles = 0
    for row in rag_cur.fetchall():
        art_id, titre, lien, source, publie, image_url, legende = row
        meta = press_metadata(
            source,
            publie.isoformat() if publie else "",
            image_url,
            legende,
        )
        rag_cur.execute(
            """
            UPDATE "KnowledgeChunk"
               SET metadata = %s, title = %s, url = %s
             WHERE "sourceType" = 'article' AND "sourceId" = %s
               AND (metadata IS DISTINCT FROM %s OR title IS DISTINCT FROM %s
                    OR url IS DISTINCT FROM %s)
            """,
            (Json(meta), titre, lien, art_id, Json(meta), titre, lien),
        )
        if rag_cur.rowcount:
            recolles += rag_cur.rowcount
    if recolles:
        print(f"[journal] {recolles} chunk(s) recolles sur la table Article (photo, legende, date)")


def sync_journal(rag_cur, path: str, stats: dict) -> None:
    """Indexe les articles consignes par les scrapers, SANS lire Convex.

    C'est le court-circuit : `convex_client._journal_article` ecrit un JSONL au
    fil du scraping, y compris quand l'ecriture Convex echoue. Le RAG n'a donc
    plus besoin que Convex reponde pour recevoir l'actualite du jour.

    Un meme lien apparait plusieurs fois (decouverte sans contenu, puis contenu
    complet, puis image) : les entrees sont fusionnees, la derniere valeur non
    vide gagne.
    """
    if not os.path.exists(path):
        print(f"[journal] aucun fichier a {path} : rien a indexer")
        return

    fusionnes: dict[str, dict] = {}
    annexes: list[dict] = []
    traites: list[str] = []
    lignes = 0
    with open(path, encoding="utf-8") as handle:
        for ligne in handle:
            ligne = ligne.strip()
            if not ligne:
                continue
            lignes += 1
            try:
                entree = json.loads(ligne)
            except json.JSONDecodeError:
                stats["errors"] += 1
                continue
            genre = entree.get("kind")
            if genre in ("image", "tag"):
                annexes.append(entree)
                continue
            lien = entree.get("link")
            if not lien:
                continue
            cible = fusionnes.setdefault(lien, {})
            for cle, valeur in entree.items():
                if valeur is not None and valeur != "":
                    cible[cle] = valeur

    print(f"[journal] {lignes} entrees -> {len(fusionnes)} articles distincts")

    for lien, article in fusionnes.items():
        if article.get("hidden"):
            stats["skipped"] += 1
            continue
        # Le journal porte des epoch ms (format Convex) ; format_press_article
        # ne les lit ainsi que sous USE_CONVEX. On normalise en datetime pour
        # que l'indexation soit independante du backend de lecture configure.
        publie = normaliser_date(article.get("publishedAt"))
        if publie is None:
            # Sans date, l'article s'indexe quand meme mais sort du fil
            # d'actualite : le lecteur ne garde que ce qu'il peut dater. La
            # fiche Article, elle, porte la date — c'est le scraper qui ne l'a
            # pas repetee dans l'entree de journal apportant le contenu. On la
            # relit plutot que de publier un article sans date (43 perdus
            # ainsi le 12/09/2026).
            rag_cur.execute('SELECT "publishedAt" FROM "Article" WHERE link = %s LIMIT 1', (lien,))
            connu = rag_cur.fetchone()
            if connu and connu[0]:
                publie = normaliser_date(connu[0])
        if not article.get("title"):
            # Le scraper de contenu ecrit PAR LIEN, sans repeter le titre : une
            # entree qui apporte le texte integral n'en porte pas. Le titre est
            # dans la fiche — l'y chercher permet d'indexer quand meme, au lieu
            # de jeter le contenu qu'on vient de scraper.
            rag_cur.execute('SELECT title FROM "Article" WHERE link = %s LIMIT 1', (lien,))
            connu = rag_cur.fetchone()
            if connu and connu[0]:
                article["title"] = connu[0]
            else:
                # Ni titre fourni, ni fiche connue : rien a indexer, on se
                # contente d'enrichir si la fiche existe.
                store_article_partiel(rag_cur, lien, article)
                stats["skipped"] += 1
                continue

        body = format_press_article({**article, "publishedAt": publie})
        if not body:
            stats["skipped"] += 1
            continue

        # Identite de l'article, par ordre de fiabilite decroissante :
        #   1. supabaseId confirme par Convex (stableId) ;
        #   2. l'id deja enregistre pour ce lien dans la table Article — c'est
        #      elle qui fait autorite quand Convex est muet, son index sur link
        #      rend la resolution immediate ;
        #   3. l'UUID que le scraper vient d'attribuer a un article neuf : c'est
        #      celui que portent ses images et ses tags, donc la fiche doit le
        #      partager, sans quoi rien ne se joint ;
        #   4. a defaut, une cle derivee du lien, stable d'un run a l'autre.
        stable_id = article.get("stableId")
        if not stable_id:
            rag_cur.execute('SELECT id FROM "Article" WHERE link = %s LIMIT 1', (lien,))
            connu = rag_cur.fetchone()
            if connu:
                stable_id = connu[0]
        source_id = stable_id or article.get("supabaseId") or surrogate_source_id(lien)
        try:
            upsert_document(
                rag_cur,
                source_type="article",
                source_id=source_id,
                title=article.get("title") or "",
                content=body,
                url=lien,
                metadata=press_metadata(
                    article.get("source"),
                    publie.isoformat() if publie else "",
                    article.get("imageUrl") or article.get("r2Url"),
                ),
                stats=stats,
            )
            traites.append(source_id)
            store_article(rag_cur, source_id, lien, article, publie)
            if stable_id:
                # Convex repond de nouveau : le document de secours eventuel,
                # indexe sous la cle derivee pendant la coupure, ferait doublon.
                # Suppression par cle exacte (index knowledge_chunk_source_idx).
                rag_cur.execute(
                    'DELETE FROM "KnowledgeChunk" WHERE "sourceType" = %s AND "sourceId" = %s',
                    ("article", surrogate_source_id(lien)),
                )
        except Exception as exc:
            stats["errors"] += 1
            print(f"  [ERR] journal {lien}: {exc}", file=sys.stderr)

    for entree in annexes:
        try:
            if entree.get("kind") == "image":
                store_image(rag_cur, entree)
            else:
                store_tag(rag_cur, entree)
        except Exception as exc:
            stats["errors"] += 1
            print(f"  [ERR] annexe {entree.get('kind')}: {exc}", file=sys.stderr)
    if annexes:
        print(f"[journal] {len(annexes)} images/tags ecrits dans le magasin de fiches")

    # APRES les annexes, jamais avant : c'est leur ecriture qui pose l'image sur
    # l'article, et c'est elle qu'on veut voir remonter dans les chunks.
    rafraichir_metadonnees(rag_cur, traites, stats)


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
        SELECT id, title, description, content, source, link, "publishedAt",
               -- imageUrl AVANT r2Url : l'exemplaire B2 est dans un seau prive
               -- (401), et MulhouseGPT ecarte toute URL backblazeb2.com avant de
               -- l'afficher. La preferer revenait a n'ecrire dans l'index que des
               -- adresses inutilisables : 18 310 articles se sont retrouves sans
               -- photo sous les sources alors que l'URL du CDN d'origine etait en
               -- base (mesure le 2026-09-16). Les deux chemins Convex de ce
               -- fichier utilisaient deja cet ordre ; seul celui-ci l'inversait.
               coalesce(NULLIF("imageUrl", ''), NULLIF("r2Url", '')) AS "imageUrl"
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
            "imageUrl": row[7],
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
                # Cle omise plutot que vide : voir press_metadata, une chaine
                # vide fait sortir l'article du fil sans erreur.
                metadata=press_metadata(None, article["publishedAt"].isoformat()
                                        if article["publishedAt"] else "", None),
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
    parser.add_argument("--journal", metavar="CHEMIN",
                        help="Indexe d'abord les articles consignes par les scrapers (JSONL ecrit via "
                             "RAG_JOURNAL_PATH), sans lire Convex. Court-circuite le maillon Convex.")
    parser.add_argument("--journal-only", action="store_true",
                        help="S'arrete apres le journal : n'interroge ni Convex ni PostgreSQL.")
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
        news_cur = news_conn.cursor() if news_conn else None
        if args.journal:
            sync_journal(rag_cur, args.journal, stats)
            # Validation immediate : le commit final est hors de portee si la
            # lecture Convex qui suit echoue, et le travail du journal — la seule
            # part qui ne depende pas de Convex — serait annule avec elle.
            rag_conn.commit()
        retires = purge_articles_masques(rag_cur)
        if retires:
            print(f"[purge] {retires} chunks d'articles masques retires de l'index")
            rag_conn.commit()
        if not args.journal_only:
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