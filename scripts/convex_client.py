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
import sys
import time
from datetime import datetime, timezone

import requests

try:  # module voisin ; absent dans certains contextes d'import isole
    import aiven_client
except ImportError:  # pragma: no cover
    aiven_client = None  # type: ignore[assignment]


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


_mutations_coupees_signalees = False


def _call(path: str, args: dict, *, mutation: bool) -> dict:
    if mutation and not ecritures_convex_actives():
        global _mutations_coupees_signalees
        if not _mutations_coupees_signalees:
            _mutations_coupees_signalees = True
            print("[convex] ecritures coupees (CONVEX_WRITES absent) : miroirs ignores",
                  file=sys.stderr)
        return {}
    url, key = _require_config()
    endpoint = f"{url}/api/{'mutation' if mutation else 'query'}"
    payload = {"path": path, "format": "json", "args": _strip_none(args) if args else {}}
    # Retry transitoire : les backfills longue durée meurent sinon sur un
    # simple « Remote end closed connection » ou un HTTP 500/503 passager.
    last_exc: Exception | None = None
    last_resp = None
    for attempt in range(4):
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
            last_resp = resp
            if resp.status_code in (429, 500, 502, 503, 504):
                time.sleep(2 * (attempt + 1))
                continue
        except requests.RequestException as exc:
            last_exc = exc
            time.sleep(2 * (attempt + 1))
            continue
        break
    else:
        if last_resp is not None and last_resp.status_code != 200:
            raise ConvexError(
                f"Convex HTTP {last_resp.status_code} ({path}) après 4 tentatives: {last_resp.text[:500]}"
            )
        raise ConvexError(f"Erreur HTTP Convex ({path}) après 4 tentatives: {last_exc}")
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

# ─────────────────────────────────────────────────────────────────────────────
# Journal RAG : court-circuit de Convex pour l'indexation
# ─────────────────────────────────────────────────────────────────────────────
#
# Le RAG de MulhouseGPT était alimenté en relisant Convex après le scraping
# (`rag_sync_articles.py`, lecture sur 25 h). Convex était donc un maillon
# obligatoire du chemin : son déploiement coupé le 11/09/2026 pour dépassement
# de quota, plus un seul article n'a atteint le RAG pendant 36 h, et « les actus
# du jour » répondaient avec l'avant-veille.
#
# Les scrapers ont pourtant l'article complet en main au moment de l'écriture.
# On le consigne donc ici, dans un fichier JSONL que `rag_sync_articles.py
# --journal` indexe en SQL direct sur l'Aiven, sans passer par Convex.
#
# Écrit AVANT de dépendre du résultat de l'appel : une écriture Convex en échec
# doit quand même laisser l'article joignable pour le RAG.

_RAG_JOURNAL_ENV = "RAG_JOURNAL_PATH"

# Depuis le 13/09/2026, l'actualite vit sur l'Aiven : le chat et les trois sites
# l'y lisent, et les articles Convex ne servaient plus qu'a remplir un quota
# depasse (6,76 Go pour 401 Mo de donnees reelles). Les ecritures d'articles y
# sont donc coupees par defaut ; le journal RAG, lui, recoit tout.
#
# Etendu le 13/09/2026 a TOUTES les ecritures : plus rien ne lit Convex — ni le
# chat, ni les trois sites, ni l'administration. Journaux de scraping,
# configuration, cinema, sorties : leurs donnees vivent dans Supabase ou sur
# l'Aiven, et les miroirs Convex ne faisaient que consommer un quota depasse.
#
# CONVEX_WRITES=1 les retablit toutes (CONVEX_ARTICLE_WRITES reste accepte).
# A poser AVANT toute reprise de Convex comme magasin, et pour les scripts de
# migration, qui doivent evidemment pouvoir ecrire.
def ecritures_convex_actives() -> bool:
    for nom in ("CONVEX_WRITES", "CONVEX_ARTICLE_WRITES"):
        if os.environ.get(nom, "").strip().lower() in ("1", "true", "on", "yes"):
            return True
    return False


# Ancien nom, conserve pour les appelants existants.
ecritures_articles_actives = ecritures_convex_actives

# Champs de fond nécessaires à l'indexation (cf. format_press_article) : ni les
# horodatages de service, ni les identifiants de jointure.
_JOURNAL_KEYS = {
    "link", "title", "source", "description", "content",
    "publishedAt", "imageUrl", "r2Url", "imageCaption", "hidden",
    # Portes par scrape_content_full : la table Article de l'Aiven les stocke,
    # les omettre laisserait ces colonnes vides pour tout nouvel article.
    "author", "category", "localImage", "scrapedAt",
    # L'UUID que le scraper attribue a un article neuf : c'est lui que portent
    # ses images et ses tags. Sans lui, une coupure Convex indexe la fiche sous
    # une cle derivee du lien pendant que les images gardent l'UUID, et les deux
    # ne se rejoignent jamais. Le risque de doublon est ecarte cote indexeur, qui
    # resout d'abord le lien dans la table Article.
    "supabaseId",
}


def _journal_ecrire(entry: dict) -> None:
    """Ajoute une entree au journal RAG. Jamais bloquant."""
    path = os.environ.get(_RAG_JOURNAL_ENV)
    if not path:
        return
    try:
        with open(path, "a", encoding="utf-8") as handle:
            handle.write(json.dumps(entry, ensure_ascii=False, default=_json_default) + "\n")
    except OSError as exc:
        print(f"[journal] ecriture impossible ({exc})", file=sys.stderr)


def _journal_images(rows: list[dict]) -> None:
    """Consigne les images d'article. L'Aiven porte depuis le 13/09/2026 une
    table ArticleImage (images multiples, legendes) que seul Convex nourrissait :
    sans ce journal, elle serait figee au chargement initial."""
    for row in rows:
        if row.get("articleId") and row.get("url"):
            _journal_ecrire({"kind": "image", **{k: v for k, v in row.items() if v is not None}})


def _journal_tags(rows: list[dict]) -> None:
    """Consigne les liaisons article <-> tag, meme raison."""
    for row in rows:
        if row.get("articleId") and row.get("tagId"):
            _journal_ecrire({"kind": "tag", "articleId": row["articleId"], "tagId": row["tagId"]})


def _journal_article(row: dict, stable_id: str | None) -> None:
    """Consigne un article pour l'indexation RAG directe. Jamais bloquant."""
    path = os.environ.get(_RAG_JOURNAL_ENV)
    if not path or not row.get("link"):
        return
    entry = {k: v for k, v in row.items() if k in _JOURNAL_KEYS and v is not None}
    # `supabaseId` — PAS l'_id Convex — est le `sourceId` du RAG : c'est ce que
    # rend get_recent_articles_with_content (« sourceId stable ») et donc ce sous
    # quoi les 127 785 articles sont deja indexes. Enregistrer l'_id ferait entrer
    # chaque article une seconde fois.
    #
    # Il n'est retenu que confirme par Convex : un scraper qui ne sait pas si
    # l'article existe deja (dedup tolerante, Convex coupe) genere un UUID NEUF
    # pour un article connu, ce qui creerait un second document. Faute de
    # confirmation, l'indexeur retombe sur une cle derivee du lien, stable d'un
    # run a l'autre, qu'il supprime au retour de Convex.
    if stable_id:
        entry["stableId"] = stable_id
    _journal_ecrire(entry)


def upsert_article(row: dict) -> dict:
    """Insère ou met à jour un article (dédup par link). Champs fournis mis à
    jour, les autres conservés. `supabaseId` (UUID frais pour les nouveaux
    articles) permet les jointures tags/images."""
    if not ecritures_articles_actives():
        # Journal seul : c'est lui qui alimente l'Aiven, magasin de reference.
        _journal_article(row, None)
        return {"created": False, "id": None, "supabaseId": row.get("supabaseId")}
    try:
        result = _call("scrapers:upsertArticle", {"row": _strip_none(row)}, mutation=True)
    except Exception:
        _journal_article(row, None)
        raise
    _journal_article(row, (result or {}).get("supabaseId"))
    return result


def get_article_by_link(link: str) -> dict | None:
    return _call("scrapers:getArticleByLink", {"link": link}, mutation=False)


def get_existing_links_for(links: list[str], batch_size: int = 100) -> set[str]:
    """Liens déjà en base parmi `links` (index by_link, par lots).

    Repli unitaire si `scrapers:getExistingLinks` n'est pas encore déployée.
    """
    existing: set[str] = set()
    if not links:
        return existing
    for i in range(0, len(links), batch_size):
        chunk = links[i : i + batch_size]
        try:
            res = _call("scrapers:getExistingLinks", {"links": chunk}, mutation=False)
            existing.update(res.get("existing") or [])
        except ConvexError:
            for link in chunk:
                if get_article_by_link(link):
                    existing.add(link)
    return existing


_indispo_signalee = False


def _signaler_convex_indisponible(exc: Exception) -> None:
    """Avertit une fois par run que la dedup est aveugle."""
    global _indispo_signalee
    if not _indispo_signalee:
        _indispo_signalee = True
        print(
            f"[convex] indisponible ({exc}) : dedup impossible, les articles seront "
            f"retraites et consignes dans le journal RAG",
            file=sys.stderr,
        )


def _aiven_dispo() -> bool:
    """L'Aiven porte-t-il la table Article ? C'est lui qui fait autorite pour la
    dedup depuis le 13/09/2026 : il est a jour, indexe sur `link`, et repond
    meme quand Convex est coupe. Indispensable avant de vider les articles cote
    Convex — sinon une table vide ferait paraitre tous les liens inconnus."""
    return bool(aiven_client and aiven_client.disponible())


def get_article_by_link_tolerant(link: str) -> dict | None:
    """`get_article_by_link` qui rend None quand Convex ne repond pas.

    Les scrapers demandent « ce lien est-il deja connu ? » AVANT de traiter
    l'article, et hors du try/except qui protege la boucle : une exception ici
    tuait le run entier avant le moindre article (constate le 11/09/2026,
    deploiement coupe pour quota). Or « je ne sais pas » doit valoir « je
    traite » : l'article sera retraite et consigne dans le journal RAG, et
    `upsert_document` ignorera un contenu inchange cote Aiven.
    """
    if _aiven_dispo():
        return aiven_client.article_par_lien(link)
    try:
        return get_article_by_link(link)
    except Exception as exc:
        _signaler_convex_indisponible(exc)
        return None


def get_existing_links_for_tolerant(links: list[str]) -> set[str]:
    """`get_existing_links_for` qui rend un ensemble vide si Convex est coupe.

    Meme raison : mieux vaut retraiter des articles deja connus que de ne rien
    collecter du tout. Voir get_article_by_link_tolerant.
    """
    if _aiven_dispo():
        return aiven_client.liens_connus(links)
    try:
        return get_existing_links_for(links)
    except Exception as exc:
        _signaler_convex_indisponible(exc)
        return set()


def get_article_by_supabase_id(article_id: str) -> dict | None:
    """Article complet (content inclus) via news_bridge:getArticleById."""
    return _call("news_bridge:getArticleById", {"id": article_id}, mutation=False)


def get_article_links(
    source: str | None = None, limit: int = 500, max_links: int | None = None
) -> list[str]:
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
        if res["isDone"] or (max_links and len(links) >= max_links):
            break
        cursor = res["cursor"]
    return links[:max_links] if max_links else links


def get_article_titles(
    source: str | None = None, limit: int = 500, max_articles: int | None = None
) -> list[dict]:
    """Tous les {link, title, imageUrl} d'articles, paginé (filtre source
    optionnel). Sans content : ~100x plus léger que getArticlesPage. Requiert la
    query `scrapers:getArticleTitlesPage` (déployer les fonctions Convex avant
    usage ; `imageUrl` est absent des déploiements antérieurs)."""
    rows: list[dict] = []
    cursor: str | None = None
    while True:
        res = _call(
            "scrapers:getArticleTitlesPage",
            {"source": source, "cursor": cursor, "limit": limit},
            mutation=False,
        )
        rows.extend(res["articles"])
        if res["isDone"] or (max_articles and len(rows) >= max_articles):
            break
        cursor = res["cursor"]
    return rows[:max_articles] if max_articles else rows


def get_articles_to_repair(
    sources: list[str],
    legacy_source: str,
    limit: int = 200,
    max_articles: int = 0,
) -> list[dict]:
    """Articles L'Alsace à réparer, du plus récent au plus ancien.

    Chaque page est un scan indexé borné (by_publishedAt desc) : `max_articles`
    permet d'arrêter la pagination dès qu'on en a assez, sans parcourir les
    ~100 000 articles d'archive.
    """
    rows: list[dict] = []
    cursor: str | None = None
    pages = 0
    while True:
        pages += 1
        res = _call(
            "scrapers:getArticlesToRepairPage",
            {
                "sources": sources,
                "legacySource": legacy_source,
                "cursor": cursor,
                "limit": limit,
            },
            mutation=False,
        )
        rows.extend(res["articles"])
        if pages % 10 == 0 and not max_articles:
            print(f"[*] Chargement des candidats : {len(rows)} trouvés...", flush=True)
        if res["isDone"] or (max_articles and len(rows) >= max_articles):
            break
        cursor = res["cursor"]
    return rows[:max_articles] if max_articles else rows


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


def get_articles_missing_content_all(limit: int = 300, max_pages: int = 200, order: str = "desc") -> list[dict]:
    """Articles lalsace.fr au contenu manquant, sans borne de date (backfill
    d'archive). Scan paginé publishedAt (défaut 'desc' : plus récents d'abord).
    Retourne les métadonnées (jamais le contenu)."""
    res = _call(
        "scrapers:getArticlesMissingContentAll",
        {"limit": limit, "maxPages": max_pages, "order": order},
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
    if not ecritures_articles_actives():
        _journal_images(rows)
        return {"inserted": 0, "updated": 0}
    try:
        return _call(
            "scrapers:upsertArticleImages",
            {"rows": [_strip_none(r) for r in rows]},
            mutation=True,
        )
    finally:
        _journal_images(rows)


def upsert_article_google_tags(rows: list[dict]) -> dict:
    """Insère les liens article<->tag (dédup par (articleId, tagId), UUIDs)."""
    if not ecritures_articles_actives():
        _journal_tags(rows)
        return {"inserted": 0}
    try:
        return _call(
            "scrapers:upsertArticleGoogleTags",
            {"rows": [_strip_none(r) for r in rows]},
            mutation=True,
        )
    finally:
        _journal_tags(rows)


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


def get_all_articles_with_content(limit: int = 300, page_size: int = 500) -> list[dict]:
    """Backfill RAG : TOUS les articles hidden=false avec contenu non vide,
    sans borne de temps, paginé du plus ancien au plus récent (cursor)."""
    articles: list[dict] = []
    cursor: str | None = None
    while True:
        res = _call(
            "scrapers:getAllArticlesWithContent",
            {"limit": limit, "cursor": cursor, "pageSize": page_size},
            mutation=False,
        )
        articles.extend(res["articles"])
        if res["isDone"]:
            break
        cursor = res["cursor"]
    return articles


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
