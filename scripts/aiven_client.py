"""Accès à la table Article de l'Aiven, pour la déduplication des scrapers.

Les scrapers demandaient à Convex « ce lien est-il déjà connu ? ». Depuis que
l'actualité vit sur l'Aiven — chargement du 13/09/2026, puis alimentation par le
journal — c'est cette base qui fait autorité : elle est à jour, elle a un index
sur `link`, et elle répond même quand Convex est coupé.

C'est aussi le préalable à la suppression des articles côté Convex : sans cette
bascule, une table Convex vidée ferait paraître tous les liens inconnus, et les
scrapers la rempliraient de nouveau au passage suivant.

Lecture seule. Les écritures passent par le journal RAG (convex_client).
"""
from __future__ import annotations

import os
import sys

import psycopg2


_connexion = None


def url() -> str | None:
    return (os.environ.get("RAG_DATABASE_URL") or "").strip() or None


def disponible() -> bool:
    return bool(url())


def _curseur():
    """Connexion paresseuse, rouverte si elle est tombée."""
    global _connexion
    if _connexion is not None and _connexion.closed:
        _connexion = None
    if _connexion is None:
        _connexion = psycopg2.connect(url())
        _connexion.autocommit = True
    return _connexion.cursor()


def liens_connus(liens: list[str]) -> set[str]:
    """Sous-ensemble de `liens` déjà présent dans la table Article.

    Une seule requête, quel que soit le nombre de liens : l'index sur `link`
    sert le `= ANY(...)`.
    """
    if not liens:
        return set()
    try:
        with _curseur() as cur:
            cur.execute('SELECT link FROM "Article" WHERE link = ANY(%s)', (list(liens),))
            return {ligne[0] for ligne in cur.fetchall()}
    except Exception as exc:
        print(f"[aiven] dedup indisponible ({exc})", file=sys.stderr)
        return set()


def lien_connu(lien: str) -> bool:
    return bool(liens_connus([lien]))


def article_par_lien(lien: str) -> dict | None:
    """Fiche minimale d'un article, pour les appelants qui lisaient Convex."""
    try:
        with _curseur() as cur:
            cur.execute(
                'SELECT id, title, link, description, "imageUrl", "imageCaption", hidden '
                'FROM "Article" WHERE link = %s LIMIT 1',
                (lien,),
            )
            r = cur.fetchone()
    except Exception as exc:
        print(f"[aiven] lecture indisponible ({exc})", file=sys.stderr)
        return None
    if not r:
        return None
    return {
        "supabaseId": r[0], "id": r[0], "title": r[1], "link": r[2],
        "description": r[3], "imageUrl": r[4], "imageCaption": r[5], "hidden": r[6],
    }


def articles_contenu_court(limit: int = 50, hours: int = 24) -> list[dict]:
    """Articles récents au contenu court ou absent, du plus récent au plus vieux.

    Reprend `scrapers:getArticlesShortContent`. Même forme de retour que Convex
    — les appelants lisent `a["source"]`, `a["link"]`, `a["title"]` — pour que
    la bascule ne les oblige à rien changer. Le contenu n'est jamais rapatrié :
    seule sa longueur sert au tri du travail restant.
    """
    try:
        with _curseur() as cur:
            cur.execute(
                'SELECT id, title, link, source, description, "imageUrl", "imageCaption" '
                'FROM "Article" '
                'WHERE hidden = false '
                '  AND (content IS NULL OR length(content) < 100) '
                '  AND "publishedAt" > NOW() - make_interval(hours => %s) '
                'ORDER BY "publishedAt" DESC LIMIT %s',
                (int(hours), int(limit)),
            )
            lignes = cur.fetchall()
    except Exception as exc:
        print(f"[aiven] articles au contenu court illisibles ({exc})", file=sys.stderr)
        return []
    return [
        {"id": r[0], "supabaseId": r[0], "title": r[1], "link": r[2], "source": r[3],
         "description": r[4], "imageUrl": r[5], "imageCaption": r[6]}
        for r in lignes
    ]


def articles_sans_contenu(limit: int = 300, order: str = "desc") -> list[dict]:
    """Articles lalsace.fr sans texte, sans borne de date (backfill d'archive).

    Reprend `scrapers:getArticlesMissingContentAll`. Convex devait paginer par
    lots de 500 en rapatriant les textes ; ici l'index fait le tri en une
    requête, et le contenu ne quitte jamais la base.
    """
    sens = "ASC" if str(order).lower() == "asc" else "DESC"
    try:
        with _curseur() as cur:
            cur.execute(
                'SELECT id, title, link, description, "imageUrl", "imageCaption" '
                'FROM "Article" '
                'WHERE hidden = false AND link LIKE %s '
                '  AND (content IS NULL OR length(content) < 150) '
                f'ORDER BY "publishedAt" {sens} LIMIT %s',
                ("%lalsace.fr%", int(limit)),
            )
            lignes = cur.fetchall()
    except Exception as exc:
        print(f"[aiven] articles sans contenu illisibles ({exc})", file=sys.stderr)
        return []
    return [
        {"supabaseId": r[0], "id": r[0], "title": r[1] or "", "link": r[2],
         "description": r[3], "imageUrl": r[4], "imageCaption": r[5]}
        for r in lignes
    ]


def articles_sans_legende(limit: int = 30) -> list[dict]:
    """Articles EBRA récents illustrés mais sans légende (rattrapage).

    Reprend `scrapers:getArticlesMissingCaptions`. L'appelant lit `row["link"]`.
    """
    try:
        with _curseur() as cur:
            cur.execute(
                'SELECT id, link FROM "Article" '
                'WHERE "imageCaption" IS NULL '
                '  AND "imageUrl" IS NOT NULL AND "imageUrl" <> \'\' '
                '  AND "publishedAt" > NOW() - INTERVAL \'14 days\' '
                '  AND (link LIKE %s OR link LIKE %s OR link LIKE %s OR link LIKE %s) '
                'ORDER BY "publishedAt" DESC LIMIT %s',
                ("%lalsace.fr%", "%dna.fr%", "%estrepublicain.fr%", "%vosgesmatin.fr%", int(limit)),
            )
            lignes = cur.fetchall()
    except Exception as exc:
        print(f"[aiven] legendes a rattraper illisibles ({exc})", file=sys.stderr)
        return []
    return [{"id": r[0], "supabaseId": r[0], "link": r[1]} for r in lignes]


def tags_actualites() -> list[dict]:
    """Tags d'actualité : [{"id", "name", "slug"}]. Reprend `scrapers:getNewsTags`."""
    try:
        with _curseur() as cur:
            cur.execute('SELECT id, name, slug FROM "NewsTag"')
            return [{"id": r[0], "name": r[1], "slug": r[2]} for r in cur.fetchall()]
    except Exception as exc:
        print(f"[aiven] tags illisibles ({exc})", file=sys.stderr)
        return []
