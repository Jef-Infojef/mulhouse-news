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
