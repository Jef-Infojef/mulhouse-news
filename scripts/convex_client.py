"""Client HTTP Convex pour les scrapers Python (Phase 3).

Remplace les accès psycopg2/SQL par des appels aux fonctions Convex du cloud
(`convex/scrapers.ts` + `convex/app.ts`), exécutés côté GitHub Actions.

Configuration (env) :
  CONVEX_DEPLOY_KEY      - deploy key `dev:<deployment>|<token>` (auth HTTP)
  NEXT_PUBLIC_CONVEX_URL - URL du déploiement, ex https://friendly-chicken-952.convex.cloud

Comportement :
  • `use_convex()` : True si CONVEX_DEPLOY_KEY (+ URL) est définie.
  • Les helpers appellent les endpoints HTTP Convex v1.43 :
      - queries  → POST {url}/api/query
      - mutations → POST {url}/api/mutation
    avec en-tête `Authorization: Convex <deploy_key>` et corps
    `{"path": "<module>:<fonction>", "format": "json", "args": {...}}`.
    (NB : l'endpoint `/api/execute` du plan d'origine n'existe pas en 1.43.)
  • Si CONVEX_DEPLOY_KEY est absente, toute tentative d'appel lève une erreur
    claire (les scripts portés basculent alors sur leur backend SQL hérité).
  • Timestamps : les helpers acceptent datetime → conversion epoch ms
    automatique (Convex stocke les timestamps en ms).
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone

import requests


def get_convex_url() -> str | None:
    return os.environ.get("NEXT_PUBLIC_CONVEX_URL") or None


def get_deploy_key() -> str | None:
    return os.environ.get("CONVEX_DEPLOY_KEY") or None


def use_convex() -> bool:
    """True si la bascule Convex est activée (clef deploy + URL définies)."""
    return bool(get_deploy_key() and get_convex_url())


class ConvexError(RuntimeError):
    """Erreur levée par une fonction Convex (ou par la couche HTTP)."""


def _require_config() -> tuple[str, str]:
    url = get_convex_url()
    key = get_deploy_key()
    if not url or not key:
        raise ConvexError(
            "Backend Convex non configuré : définir CONVEX_DEPLOY_KEY "
            "et NEXT_PUBLIC_CONVEX_URL (ou lancer avec USE_CONVEX=1)."
        )
    return url, key


def to_epoch_ms(value) -> int | None:
    """Convertit datetime (naïf = UTC) en epoch ms ; passe les nombres tels quels."""
    if value is None:
        return None
    if isinstance(value, datetime):
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return int(value.timestamp() * 1000)
    return int(value)


# Champs optionnels des fonctions Convex : Convex refuse `null` sur un champ
# v.optional(v.string()) — il faut l'OMETTRE. Les champs `null` explicites dont
# le validateur attend un null/string (ex. cursor de pagination) sont conservés.
_STRIP_NONE_KEYS = {
    "title", "imageUrl", "imageCaption", "source", "description",
    "publishedAt", "scrapedAt", "createdAt", "updatedAt", "content",
    "localImage", "r2Url", "hidden", "supabaseId",
    "caption", "position", "finishedAt", "errorMessage", "details",
    # Sorties (outings / outingCategories / outingTags)
    "date", "endDate", "location", "price", "link",
    "associationId", "slug", "color", "name",
    "outingId", "categoryId",
}


def _strip_none(payload: dict) -> dict:
    return {k: v for k, v in payload.items() if not (v is None and k in _STRIP_NONE_KEYS)}


def _json_default(value):
    """Sérialise datetime → epoch ms (Convex stocke les timestamps en ms)."""
    if isinstance(value, datetime):
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return int(value.timestamp() * 1000)
    raise TypeError(f"Object of type {value.__class__.__name__} is not JSON serializable")


def _call(path: str, args: dict, *, mutation: bool) -> dict:
    url, key = _require_config()
    endpoint = f"{url}/api/{'mutation' if mutation else 'query'}"
    payload = {"path": path, "format": "json", "args": _strip_none(args) if args else {}}
    try:
        resp = requests.post(
            endpoint,
            data=json.dumps(payload, default=_json_default),
            headers={
                "Authorization": f"Convex {key}",
                "Content-Type": "application/json",
            },
            timeout=90,
        )
    except requests.RequestException as exc:
        raise ConvexError(f"Erreur HTTP Convex ({path}): {exc}") from exc
    if resp.status_code != 200:
        raise ConvexError(
            f"Convex HTTP {resp.status_code} ({path}): {resp.text[:500]}"
        )
    data = resp.json()
    if data.get("status") != "success":
        raise ConvexError(
            f"Convex UDF en erreur ({path}): {data.get('errorMessage', data)}"
        )
    return data.get("value")


# ─────────────────────────────────────────────────────────────────────────────
# Articles
# ─────────────────────────────────────────────────────────────────────────────

def upsert_article(row: dict) -> dict:
    """Insère ou met à jour un article (dédup par link). Champs fournis mis à
    jour, les autres conservés. `supabaseId` (UUID frais pour les nouveaux
    articles) permet les jointures tags/images."""
    return _call("scrapers:upsertArticle", {"row": _strip_none(row)}, mutation=True)


def get_article_by_link(link: str) -> dict | None:
    return _call("scrapers:getArticleByLink", {"link": link}, mutation=False)


def get_article_links(source: str | None = None, limit: int = 500) -> list[str]:
    """Toutes les links d'articles, paginées (filtre source optionnel)."""
    links: list[str] = []
    cursor: str | None = None
    while True:
        res = _call(
            "scrapers:getArticleLinks",
            {"source": source, "cursor": cursor, "limit": limit},
            mutation=False,
        )
        links.extend(res["links"])
        if res["isDone"]:
            break
        cursor = res["cursor"]
    return links


def get_article_by_title_recent(title: str, hours: int = 48) -> dict | None:
    return _call(
        "scrapers:getArticleByTitleRecent",
        {"title": title, "hours": hours},
        mutation=False,
    )


def get_article_by_image(image_url: str, start_ms: int, end_ms: int) -> dict | None:
    return _call(
        "scrapers:getArticleByImage",
        {"imageUrl": image_url, "startMs": start_ms, "endMs": end_ms},
        mutation=False,
    )


def get_articles_short_content(limit: int = 50, hours: int = 24) -> list[dict]:
    """Articles récents (hidden=false) au contenu court/absent, trié publishedAt
    desc. Retourne les métadonnées (jamais le contenu)."""
    res = _call(
        "scrapers:getArticlesShortContent",
        {"limit": limit, "hours": hours},
        mutation=False,
    )
    return res["articles"]


def get_articles_missing_captions(limit: int = 30) -> list[dict]:
    """Articles EBRA récents avec imageUrl mais sans imageCaption (rattrapage)."""
    res = _call(
        "scrapers:getArticlesMissingCaptions",
        {"limit": limit},
        mutation=False,
    )
    return res["rows"]


def delete_article_by_link(link: str) -> dict:
    return _call("scrapers:deleteArticleByLink", {"link": link}, mutation=True)


# ─────────────────────────────────────────────────────────────────────────────
# Images & tags
# ─────────────────────────────────────────────────────────────────────────────

def upsert_article_images(rows: list[dict]) -> dict:
    """Upsert d'images d'articles (dédup par (articleId, url)). `articleId` est
    l'UUID Supabase d'origine (champ supabaseId de l'article)."""
    return _call(
        "scrapers:upsertArticleImages",
        {"rows": [_strip_none(r) for r in rows]},
        mutation=True,
    )


def upsert_article_google_tags(rows: list[dict]) -> dict:
    """Insère les liens article<->tag (dédup par (articleId, tagId), UUIDs)."""
    return _call(
        "scrapers:upsertArticleGoogleTags",
        {"rows": [_strip_none(r) for r in rows]},
        mutation=True,
    )


def get_news_tags() -> list[dict]:
    """Tous les tags : [{"id": <supabaseId>, "name", "slug"}]."""
    return _call("scrapers:getNewsTags", {}, mutation=False)


# ─────────────────────────────────────────────────────────────────────────────
# Sorties / agenda (module convex/outings.ts)
# ─────────────────────────────────────────────────────────────────────────────

def upsert_outing(row: dict) -> dict:
    """Insère ou met à jour une sortie (dédup par supabaseId, UUID Supabase).

    `row` attend : supabaseId, associationId, title, date (datetime → epoch ms
    automatique) + optionnels description, imageUrl, endDate, location, price,
    link, hidden, createdAt, updatedAt. Les champs absents/None ne sont pas
    écrasés sur une sortie existante."""
    return _call("outings:upsertOuting", {"row": _strip_none(row)}, mutation=True)


def upsert_outing_category(row: dict) -> dict:
    """Insère ou met à jour une catégorie (dédup par supabaseId).

    `row` : supabaseId, associationId, name, slug + optionnels color, createdAt,
    updatedAt."""
    return _call("outings:upsertOutingCategory", {"row": _strip_none(row)}, mutation=True)


def upsert_outing_tag(row: dict) -> dict:
    """Insère le lien sortie↔catégorie (dédup par (outingId, categoryId)).

    `row` : supabaseId (UUID v5 déterministe du couple), outingId (supabaseId
    de la sortie), categoryId (supabaseId de la catégorie)."""
    return _call("outings:upsertOutingTag", {"row": _strip_none(row)}, mutation=True)


def get_outing_categories() -> list[dict]:
    """Toutes les catégories : [{"supabaseId", "name", "slug", "color"}]."""
    return _call("outings:getOutingCategories", {}, mutation=False)


def get_recent_outings(limit: int = 3000) -> list[dict]:
    """Sorties à venir (hidden=false, 90 j) triées par date asc — pont RAG.
    `id` = supabaseId ; `categories` = [{"name", ...}]."""
    res = _call("outings:getRecentOutings", {"limit": limit}, mutation=False)
    return res["outings"]


def delete_outing_by_supabase_id(supabase_id: str) -> dict:
    """Supprime une sortie + ses tags (cascade manuelle)."""
    return _call("outings:deleteOutingBySupabaseId", {"supabaseId": supabase_id}, mutation=True)


# ─────────────────────────────────────────────────────────────────────────────
# RAG
# ─────────────────────────────────────────────────────────────────────────────

def get_recent_articles_with_content(limit: int = 250, hours: int = 25) -> list[dict]:
    """Articles récents hidden=false avec contenu non vide (sync RAG).
    `id` = supabaseId (sourceId stable) ; `content` renvoyé (usage RAG)."""
    res = _call(
        "scrapers:getRecentArticlesWithContent",
        {"limit": limit, "hours": hours},
        mutation=False,
    )
    return res["articles"]


# ─────────────────────────────────────────────────────────────────────────────
# AppConfig
# ─────────────────────────────────────────────────────────────────────────────

def get_app_config(key: str) -> str | None:
    res = _call("app:getAppConfig", {"key": key}, mutation=False)
    return res.get("value")


def set_app_config(key: str, value: str) -> dict:
    return _call("app:setAppConfig", {"key": key, "value": value}, mutation=True)


# ─────────────────────────────────────────────────────────────────────────────
# ScrapingLog
# ─────────────────────────────────────────────────────────────────────────────

def insert_scraping_log(
    started_at,
    status: str,
    *,
    is_connected: bool = True,
    articles_count: int = 0,
    success_count: int = 0,
    error_count: int = 0,
    details=None,
    error_message: str | None = None,
    finished_at=None,
) -> dict:
    """Insère un ScrapingLog (aucune clé naturelle, simple insert)."""
    return _call(
        "scrapers:insertScrapingLog",
        _strip_none(
            {
                "startedAt": to_epoch_ms(started_at),
                "finishedAt": to_epoch_ms(finished_at),
                "status": status,
                "isConnected": bool(is_connected),
                "articlesCount": int(articles_count),
                "successCount": int(success_count),
                "errorCount": int(error_count),
                "details": details,
                "errorMessage": error_message,
            }
        ),
        mutation=True,
    )
