"""Script de migration : Déduplication DNA / L'Alsace.

1. Identifie tous les articles DNA dans la base de données.
2. Si l'article L'Alsace existe déjà en BDD :
   - Enrichit l'article L'Alsace (contenu, image, tags) si manquant.
   - Supprime l'article DNA en doublon.
3. Si l'article L'Alsace n'est pas en BDD :
   - Transforme l'article DNA en article L'Alsace (URL lalsace.fr, source L'Alsace, titre adapté).
"""

import os
import sys
import re
import unicodedata
from datetime import datetime, timezone
import dotenv
dotenv.load_dotenv(r'C:\dev\mulhouse-news\.env.local')
dotenv.load_dotenv(r'C:\dev\mulhouse-news\.env')
import psycopg2
from psycopg2.extras import RealDictCursor

def clean_title(t):
    if not t:
        return ""
    t = re.sub(r"\s*[-|]\s*(DNA|L'Alsace|Les Dernières Nouvelles d'Alsace|Dna\.fr|lalsace\.fr|dna\.fr).*$", "", t, flags=re.I)
    t = re.sub(r"^[A-Za-zÀ-ÿ0-9\s\-–—\(\)]+\.\s*", "", t)
    t = "".join(c for c in unicodedata.normalize("NFKD", t) if not unicodedata.combining(c))
    t = re.sub(r"[^\w\s]", " ", t.lower())
    return re.sub(r"\s+", " ", t).strip()

def get_slug(url):
    try:
        path = url.split("?")[0].rstrip("/")
        slug = path.split("/")[-1].lower()
        slug = re.sub(r"-[a-z0-9]{4,8}$", "", slug)
        return slug
    except Exception:
        return ""

def update_title_for_alsace(title):
    if not title:
        return title
    t = re.sub(r"\s*[-|]\s*(DNA - Les Derni[èe]res Nouvelles d'Alsace|DNA|Dna\.fr|dna\.fr)\s*$", " - L'Alsace", title, flags=re.I)
    return t

def run_migration(dry_run=False):
    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        raise RuntimeError("DATABASE_URL is not set")
    clean_url = db_url.replace("?pgbouncer=true", "").replace("&pgbouncer=true", "")
    conn = psycopg2.connect(clean_url)
    cur = conn.cursor(cursor_factory=RealDictCursor)

    print(f"=== MIGRATION DNA -> L'ALSACE (dry_run={dry_run}) ===")

    # 1. Fetch DNA articles
    cur.execute("""
        SELECT id, title, link, "imageUrl", "imageCaption", source, description, "publishedAt", content, "localImage", "r2Url", hidden
        FROM "Article"
        WHERE link LIKE '%dna.fr%' OR source ILIKE '%dna%'
        ORDER BY "publishedAt" DESC
    """)
    dna_articles = cur.fetchall()
    print(f"Total DNA articles in DB: {len(dna_articles)}")

    # 2. Fetch L'Alsace articles
    cur.execute("""
        SELECT id, title, link, "imageUrl", "imageCaption", source, description, "publishedAt", content, "localImage", "r2Url", hidden
        FROM "Article"
        WHERE link LIKE '%lalsace.fr%' OR source ILIKE '%alsace%'
        ORDER BY "publishedAt" DESC
    """)
    alsace_articles = cur.fetchall()
    print(f"Total L'Alsace articles in DB: {len(alsace_articles)}")

    # Build index structures
    alsace_by_link = {}
    alsace_by_clean_title = {}
    alsace_by_slug = {}

    for a in alsace_articles:
        link = a["link"]
        alsace_by_link[link] = a
        alsace_by_link[link.replace("http://", "https://")] = a
        ct = clean_title(a["title"])
        if ct and len(ct) > 10:
            alsace_by_clean_title.setdefault(ct, []).append(a)
        slug = get_slug(link)
        if slug and len(slug) > 10:
            alsace_by_slug.setdefault(slug, []).append(a)

    to_delete = []   # (dna, alsace_match, reason)
    to_convert = []  # (dna, target_link, target_title)
    seen_target_links = set(alsace_by_link.keys())

    for dna in dna_articles:
        dna_link = dna["link"]
        direct_alsace_https = dna_link.replace("dna.fr", "lalsace.fr").replace("http://", "https://")
        direct_alsace_http = dna_link.replace("dna.fr", "lalsace.fr").replace("https://", "http://")
        
        match = None
        reason = None
        
        # 1. Direct link
        if direct_alsace_https in alsace_by_link:
            match = alsace_by_link[direct_alsace_https]
            reason = "direct_link"
        elif direct_alsace_http in alsace_by_link:
            match = alsace_by_link[direct_alsace_http]
            reason = "direct_link"
            
        # 2. Slug match
        if not match:
            dna_slug = get_slug(dna_link)
            if dna_slug in alsace_by_slug:
                candidates = alsace_by_slug[dna_slug]
                if dna["publishedAt"]:
                    close = [c for c in candidates if c["publishedAt"] and abs((c["publishedAt"] - dna["publishedAt"]).total_seconds()) < 60*86400]
                    if close:
                        match = min(close, key=lambda c: abs((c["publishedAt"] - dna["publishedAt"]).total_seconds()))
                        reason = "slug_match"
                else:
                    match = candidates[0]
                    reason = "slug_match"

        # 3. Clean title match
        if not match:
            ct = clean_title(dna["title"])
            if ct in alsace_by_clean_title:
                candidates = alsace_by_clean_title[ct]
                if dna["publishedAt"]:
                    close = [c for c in candidates if c["publishedAt"] and abs((c["publishedAt"] - dna["publishedAt"]).total_seconds()) < 60*86400]
                    if close:
                        match = min(close, key=lambda c: abs((c["publishedAt"] - dna["publishedAt"]).total_seconds()))
                        reason = "title_match"
                else:
                    match = candidates[0]
                    reason = "title_match"

        if match:
            to_delete.append((dna, match, reason))
        else:
            target_link = dna_link.replace("dna.fr", "lalsace.fr")
            if target_link in seen_target_links:
                match = alsace_by_link.get(target_link)
                to_delete.append((dna, match, "converted_link_collision"))
            else:
                seen_target_links.add(target_link)
                target_title = update_title_for_alsace(dna["title"])
                to_convert.append((dna, target_link, target_title))

    print(f"\nPlan de traitement:")
    print(f" - Doublons DNA à supprimer (L'Alsace conservé) : {len(to_delete)}")
    print(f" - Articles DNA à remplacer/convertir en L'Alsace : {len(to_convert)}")

    if dry_run:
        print("\n[DRY RUN] Aucune modification effectuée en base.")
        conn.close()
        return

    # EXECUTION
    deleted_count = 0
    enriched_content_count = 0
    enriched_image_count = 0
    migrated_tags_count = 0
    converted_count = 0

    print("\nÉtape 1: Traitement des doublons (enrichissement + suppression DNA)...")
    for dna, alsace, reason in to_delete:
        dna_id = dna["id"]
        
        if alsace:
            alsace_id = alsace["id"]
            patch_fields = []
            patch_params = []
            
            if (not alsace["content"] or len(alsace["content"]) < 100) and (dna["content"] and len(dna["content"]) >= 100):
                patch_fields.append('content = %s')
                patch_params.append(dna["content"])
                enriched_content_count += 1
                
            if not alsace["imageUrl"] and dna["imageUrl"]:
                patch_fields.append('"imageUrl" = %s')
                patch_params.append(dna["imageUrl"])
                if dna["imageCaption"] and not alsace["imageCaption"]:
                    patch_fields.append('"imageCaption" = %s')
                    patch_params.append(dna["imageCaption"])
                enriched_image_count += 1
                
            if (not alsace["description"] or len(alsace["description"]) < 20) and (dna["description"] and len(dna["description"]) >= 20):
                patch_fields.append('description = %s')
                patch_params.append(dna["description"])

            if patch_fields:
                patch_fields.append('"updatedAt" = NOW()')
                sql_update = f'UPDATE "Article" SET {", ".join(patch_fields)} WHERE id = %s'
                patch_params.append(alsace_id)
                cur.execute(sql_update, patch_params)

            cur.execute('SELECT "tagId" FROM "ArticleGoogleTag" WHERE "articleId" = %s', (dna_id,))
            dna_tags = [r["tagId"] for r in cur.fetchall()]
            for tag_id in dna_tags:
                cur.execute("""
                    INSERT INTO "ArticleGoogleTag" ("articleId", "tagId")
                    VALUES (%s, %s)
                    ON CONFLICT DO NOTHING
                """, (alsace_id, tag_id))
                migrated_tags_count += 1

        cur.execute('DELETE FROM "Article" WHERE id = %s', (dna_id,))
        deleted_count += 1

    print("\nÉtape 2: Conversion en place des articles DNA sans doublon...")
    for dna, target_link, target_title in to_convert:
        dna_id = dna["id"]
        cur.execute("""
            UPDATE "Article"
            SET link = %s,
                title = %s,
                source = 'L''Alsace',
                "updatedAt" = NOW()
            WHERE id = %s
        """, (target_link, target_title, dna_id))
        converted_count += 1

    conn.commit()
    print("\n--- RÉSULTATS DE LA MIGRATION ---")
    print(f"Doublons DNA supprimés : {deleted_count}")
    print(f"Articles L'Alsace enrichis en contenu : {enriched_content_count}")
    print(f"Articles L'Alsace enrichis en image : {enriched_image_count}")
    print(f"Tags Google migrés : {migrated_tags_count}")
    print(f"Articles DNA convertis en L'Alsace : {converted_count}")

    cur.execute("SELECT count(*) FROM \"Article\" WHERE link LIKE '%dna.fr%' OR source ILIKE '%dna%'")
    remaining_dna = cur.fetchone()["count"]
    cur.execute("SELECT count(*) FROM \"Article\" WHERE link LIKE '%lalsace.fr%' OR source ILIKE '%alsace%'")
    final_alsace = cur.fetchone()["count"]
    cur.execute("SELECT count(*) FROM \"Article\"")
    final_total = cur.fetchone()["count"]

    print(f"\nVérification finale en base de données :")
    print(f" - Articles DNA restants : {remaining_dna}")
    print(f" - Articles L'Alsace au total : {final_alsace}")
    print(f" - Total articles en BDD : {final_total}")

    conn.close()

if __name__ == "__main__":
    dry_run = "--dry-run" in sys.argv
    run_migration(dry_run=dry_run)
