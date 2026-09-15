"""Vide le stock d'articles L'Alsace en attente de contenu, en une commande.

Le cron `scrape-news` ne se déclenche qu'environ 7 fois par jour là où il en
demande 96 (l'événement `schedule` de GitHub est abandonné en masse sous
charge), et chaque passage ne traite qu'un lot. Les articles découverts par
sitemap mais jamais ouverts s'accumulent donc, avec un titre et pas de texte.

Ce script fait à la main ce que le cron ferait s'il tournait :

  1. `scrape_content_full --archive` ouvre les articles sans texte (GRDC +
     cookie EBRA) et consigne ce qu'il lit dans le journal RAG ;
  2. `rag_sync_articles --journal` déverse ce journal dans `Article` et
     `KnowledgeChunk` sur l'Aiven.

L'étape 2 n'est pas optionnelle : depuis que Convex est coupé pour quota, le
scraper de contenu n'écrit plus nulle part d'autre que le journal. Sans elle,
le texte récupéré est perdu à la fin du run.

Usage:
  python scripts/rattrape_contenu_en_attente.py                 # 50 plus récents
  python scripts/rattrape_contenu_en_attente.py --limit 200
  python scripts/rattrape_contenu_en_attente.py --order asc     # les plus vieux
  python scripts/rattrape_contenu_en_attente.py --compter       # ne fait rien, compte
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
from datetime import datetime

import psycopg2
from dotenv import load_dotenv

_racine = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for _env in (".envenv", ".env.local", ".env"):
    load_dotenv(os.path.join(_racine, _env))

# Même critère que `aiven_client.articles_sans_contenu` : sous 150 caractères,
# il n'y a qu'un chapô, pas un article.
STOCK_SQL = (
    'SELECT count(*) FROM "Article" '
    "WHERE hidden = false AND link LIKE %s "
    "  AND (content IS NULL OR length(content) < 150)"
)


def stock(cur, recent_seulement: bool) -> int:
    sql = STOCK_SQL
    args: list = ["%lalsace.fr%"]
    if recent_seulement:
        sql += ' AND "publishedAt" > NOW() - INTERVAL %s'
        args.append("30 days")
    cur.execute(sql, args)
    return cur.fetchone()[0]


def lancer(etape: str, cmd: list[str], env: dict) -> int:
    print(f"\n=== {etape} ===", flush=True)
    return subprocess.run(cmd, env=env, cwd=_racine).returncode


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--limit", type=int, default=50, help="articles à ouvrir (défaut : 50)")
    p.add_argument("--order", choices=["desc", "asc"], default="desc",
                   help="desc : les plus récents d'abord (défaut)")
    p.add_argument("--compter", action="store_true", help="afficher le stock et sortir")
    p.add_argument("--skip-images", action="store_true",
                   help="ne pas télécharger les images (utile sans les clés B2)")
    args = p.parse_args()

    rag_url = os.environ.get("RAG_DATABASE_URL")
    if not rag_url:
        print("RAG_DATABASE_URL manquant : c'est la base qui fait autorité.", file=sys.stderr)
        return 1

    conn = psycopg2.connect(rag_url)
    conn.autocommit = True
    cur = conn.cursor()

    avant_tout = stock(cur, False)
    avant_recent = stock(cur, True)
    print(f"Stock L'Alsace sans contenu : {avant_tout} au total, "
          f"dont {avant_recent} publiés dans les 30 derniers jours")
    if args.compter:
        return 0

    env = dict(os.environ)
    env["USE_CONVEX"] = "1"
    # Le journal est le seul chemin d'écriture depuis la coupure Convex : sans
    # ce chemin, `scrape_content_full` lirait les articles pour rien.
    journal = os.path.join(_racine, "rag-journal.jsonl")
    env["RAG_JOURNAL_PATH"] = journal
    if os.path.exists(journal):
        # Repartir d'un journal vide : les entrées d'un run précédent ont déjà
        # été indexées, les réindexer ferait du travail en double.
        os.replace(journal, journal + ".precedent")

    debut = datetime.now()
    cmd = [sys.executable, "scripts/scrape_content_full.py", "--archive",
           "--limit", str(args.limit), "--order", args.order, "--worklist-aiven"]
    if args.skip_images:
        cmd.append("--skip-images")
    if lancer("1/2 — ouverture des articles (GRDC + cookie EBRA)", cmd, env) != 0:
        print("[!] le scraper de contenu a échoué ; le journal est indexé quand même",
              file=sys.stderr)

    lancer("2/2 — indexation du journal vers Article + KnowledgeChunk",
           [sys.executable, "scripts/rag_sync_articles.py",
            "--journal", journal, "--journal-only"], env)

    apres_tout = stock(cur, False)
    apres_recent = stock(cur, True)
    duree = (datetime.now() - debut).total_seconds()
    print(f"\n=== bilan ({duree:.0f} s) ===")
    print(f"  total   : {avant_tout} -> {apres_tout}  ({avant_tout - apres_tout} libérés)")
    print(f"  30 jours: {avant_recent} -> {apres_recent}  ({avant_recent - apres_recent} libérés)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
