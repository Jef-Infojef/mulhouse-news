"""Suivi d'avancée de la migration L'Alsace (Supabase → Convex) + RAG.

Lit l'état dans les deux bases :
  • Supabase (DATABASE_URL) : articles L'Alsace, avec contenu, vides.
  • Convex  (CONVEX_DEPLOY_KEY + NEXT_PUBLIC_CONVEX_URL) : articles présents,
    et (optionnel) nombre de KnowledgeChunk RAG indexés.

Usage :
  python scripts/status_migration.py
  python scripts/status_migration.py --rag      # inclut le comptage RAG (Aiven)
"""

import argparse
import os
from datetime import datetime

import psycopg2
from dotenv import load_dotenv

import convex_client

load_dotenv(".env.local")
load_dotenv(".env")


def fmt_ms(ms):
    if not ms:
        return "-"
    try:
        return datetime.fromtimestamp(ms / 1000).strftime("%Y-%m-%d")
    except Exception:
        return "-"


def count_supabase_alsace():
    url = os.environ.get("DATABASE_URL", "").replace("?pgbouncer=true", "").replace("&pgbouncer=true", "")
    conn = psycopg2.connect(url)
    cur = conn.cursor()
    cur.execute("""
        SELECT COUNT(*),
               COUNT(*) FILTER (WHERE content IS NOT NULL AND LENGTH(content) >= 150),
               COUNT(*) FILTER (WHERE content IS NULL OR LENGTH(content) < 150)
        FROM "Article" WHERE link LIKE '%%lalsace.fr%%'
    """)
    total, ok, vides = cur.fetchone()
    cur.close()
    conn.close()
    return total, ok, vides


def count_convex_alsace():
    """Compte les articles lalsace.fr présents dans Convex (scan paginé par lien)."""
    links = set()
    try:
        for link in convex_client.get_article_links():
            if "lalsace.fr" in link:
                links.add(link)
    except Exception as e:
        return None, f"erreur Convex: {e}"
    return len(links), None


def count_rag():
    try:
        url = os.environ.get("RAG_DATABASE_URL", "").replace("?pgbouncer=true", "").replace("&pgbouncer=true", "")
        conn = psycopg2.connect(url)
        cur = conn.cursor()
        cur.execute('SELECT COUNT(*) FROM "KnowledgeChunk" WHERE "sourceType" = %s', ("article",))
        n = cur.fetchone()[0]
        cur.close()
        conn.close()
        return n
    except Exception as e:
        return f"erreur RAG: {e}"


def main():
    parser = argparse.ArgumentParser(description="Suivi migration L'Alsace Supabase → Convex + RAG")
    parser.add_argument("--rag", action="store_true", help="Inclure le comptage RAG (KnowledgeChunk)")
    args = parser.parse_args()

    print("=== SUIVI MIGRATION L'ALSACE ===\n")

    total, ok, vides = count_supabase_alsace()
    print(f"[Supabase] articles L'Alsace : {total}")
    print(f"   ├─ avec contenu OK   : {ok}")
    print(f"   └─ vides (<150)      : {vides}")

    print()
    print("[Convex] articles L'Alsace présents :")
    n_convex, err = count_convex_alsace()
    if err:
        print(f"   {err}")
    else:
        print(f"   {n_convex} liens lalsace.fr")
        # déjà migrés = ceux présents dans Convex
        deja = min(n_convex, total)
        restant = max(0, total - deja)
        print(f"   → déjà dans Convex : ~{deja}")
        print(f"   → à migrer (estimé) : ~{restant}")
        pct = (deja / total * 100) if total else 0
        print(f"   → progression : {pct:.1f}%")

    if args.rag:
        print()
        n_rag = count_rag()
        if isinstance(n_rag, str):
            print(f"[RAG] {n_rag}")
        else:
            print(f"[RAG] KnowledgeChunk (articles) indexés : {n_rag}")


if __name__ == "__main__":
    main()