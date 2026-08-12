import os, psycopg2
from dotenv import load_dotenv

load_dotenv(".env.local")
load_dotenv(".env")

URL = os.environ.get("DATABASE_URL")
if not URL:
    raise SystemExit("DATABASE_URL not set")
clean = URL.replace("?pgbouncer=true", "").replace("&pgbouncer=true", "")
conn = psycopg2.connect(clean)
cur = conn.cursor()

# Cadre temporel : 3 derniers jours
cur.execute("SELECT NOW()")
now = cur.fetchone()[0]
print(f"DB NOW() = {now}")

cur.execute("""
    SELECT id, title, link, "publishedAt",
           LENGTH(content)                 AS content_len,
           (content IS NULL)               AS is_null,
           "imageUrl" IS NOT NULL AND "imageUrl" <> '' AS has_image,
           COALESCE("imageCaption",'')     AS caption,
           "updatedAt",
           (SELECT COUNT(*) FROM "ArticleImage" ai WHERE ai."articleId" = a.id) AS n_images,
           (SELECT COUNT(*) FROM "ArticleImage" ai2 WHERE ai2."articleId" = a.id AND ai2."source"='hero') AS n_hero,
           (SELECT COUNT(*) FROM "ArticleImage" ai3 WHERE ai3."articleId" = a.id AND ai3."source"='gallery') AS n_gal
    FROM "Article" a
    WHERE (source ILIKE '%alsace%' OR link LIKE '%lalsace.fr%')
      AND "publishedAt" > NOW() - INTERVAL '3 days'
    ORDER BY "publishedAt" DESC
""")
rows = cur.fetchall()
print(f"\n=== Articles L'Alsace (3 derniers jours) : {len(rows)} ===\n")

short = 0
nullc = 0
noimg = 0
for (aid, title, link, pub, clen, isnull, hasimg, cap, upd, nimg, nhero, ngal) in rows:
    if isnull or (clen is not None and clen < 150):
        short += 1
        flag = "COMPLET" if (clen or 0) >= 150 else "COURT/NULL"
    else:
        short += 0
        flag = "COMPLET" if (clen or 0) >= 150 else "COURT/NULL"
    if not hasimg:
        noimg += 1
    print(f"[{flag}] len={clen if clen is not None else 'NULL':>6} imgs(H/G)={nhero}/{ngal} cap={bool(cap)} | {(pub or '').strftime('%m-%d %H:%M')} | {title[:50]}")

print(f"""
--- RÉCAP ---
Total articles : {len(rows)}
Contenu NULL : {sum(1 for r in rows if r[5])}
Contenu < 150 chars (court) : {sum(1 for r in rows if not r[5] and (r[4] or 0) < 150)}
Sans imageUrl : {noimg}
Articles avec 0 image de galerie (ArticleImage) : {sum(1 for r in rows if r[11] == 0)}
""")

# Récap des logs de scraping sur la période
cur.execute("""
    SELECT "startedAt", status, "articlesCount", "successCount", "errorCount"
    FROM "ScrapingLog"
    WHERE "startedAt" > NOW() - INTERVAL '3 days'
    ORDER BY "startedAt" DESC
""")
logs = cur.fetchall()
print(f"--- SCRAPING LOGS (3 derniers jours) : {len(logs)} ---")
for l in logs:
    print(f"{l[0]} | {l[1]:<12} | arts={l[2]} succ={l[3]} err={l[4]}")

# Liste détaillée des articles sans image de galerie
print("\n--- ARTICLES SANS IMAGE DE GALERIE (détail) ---")
for r in rows:
    if r[11] == 0:
        print(f"len={r[4]} | {r[3].strftime('%m-%d %H:%M')} | {r[1]}")
        print(f"   LINK: {r[2]}")
        print(f"   IMAGE HERO: {r[12] if False else 'n/a'}")
        # imageUrl
        cur.execute('SELECT "imageUrl", "imageCaption" FROM "Article" WHERE id=%s', (r[0],))
        iu = cur.fetchone()
        print(f"   imageUrl: {iu[0]}")
        print(f"   imageCaption: {iu[1]}")

# Répartition par source des articles L'Alsace
cur.execute("""
    SELECT COALESCE(source,'(NULL)'), COUNT(*)
    FROM "Article"
    WHERE (source ILIKE '%alsace%' OR link LIKE '%lalsace.fr%')
      AND "publishedAt" > NOW() - INTERVAL '3 days'
    GROUP BY 1 ORDER BY 2 DESC
""")
print("\n--- PAR SOURCE ---")
for s, c in cur.fetchall():
    print(f"{s}: {c}")

cur.close(); conn.close()
