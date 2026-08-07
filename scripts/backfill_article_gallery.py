import sys, os, time, random, re
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))
from dotenv import load_dotenv
load_dotenv(".env.local")
load_dotenv(".env")
import psycopg2
import scrape_content_full as scf


def get_db_connection():
    return psycopg2.connect(os.environ["DATABASE_URL"].replace("?pgbouncer=true", ""))


def build_cookies(conn):
    """Reconstruit les cookies EBRA comme dans scrape_content_full.main()."""
    db_session = scf.get_app_config(conn, "EBRA_SESSION")
    db_poool = scf.get_app_config(conn, "EBRA_POOOL")
    if not db_session:
        return {}, False
    s_val = db_session.strip().replace('"', '').replace("'", "")
    if "2=" in s_val:
        s_val = s_val[s_val.find("2="):].split(";")[0].strip()
    p_val = db_poool.strip().replace('"', '').replace("'", "") if db_poool else "9aab6ee3-fda6-43fc-a90e-29de3c73d8f7"
    if "_poool=" in p_val:
        p_val = p_val.split("_poool=")[1].split(";")[0]
    uuid_match = re.search(r'[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}', p_val)
    if uuid_match:
        p_val = uuid_match.group(0)
    cookies = {
        ".XCONNECT_SESSION": s_val,
        ".XCONNECTKeepAlive": "2=1",
        ".XCONNECT": "2=1",
        "_poool": p_val,
    }
    return cookies, True


def main():
    days = int(sys.argv[sys.argv.index("--days") + 1]) if "--days" in sys.argv else 14
    limit = int(sys.argv[sys.argv.index("--limit") + 1]) if "--limit" in sys.argv else None
    if "--sources" in sys.argv:
        sources = sys.argv[sys.argv.index("--sources") + 1].split(",")
    else:
        sources = None

    conn = get_db_connection()
    cur = conn.cursor()
    cookies_dict, alsace_active = build_cookies(conn)

    source_filter = ""
    if sources:
        placeholders = ", ".join(["%s"] * len(sources))
        source_filter = f' AND a.source IN ({placeholders})'

    cur.execute(("""
        SELECT a.id, a.link, a."imageUrl", a."imageCaption"
        FROM "Article" a
        WHERE a."publishedAt" > NOW() - INTERVAL '%s days'
          AND a."imageUrl" IS NOT NULL AND a."imageUrl" NOT IN ('', 'null')
          AND a.content IS NOT NULL AND LENGTH(a.content) >= 150
          %s
          AND NOT EXISTS (
              SELECT 1 FROM "ArticleImage" ai
              WHERE ai."articleId" = a.id AND ai.source = 'gallery'
          )
        ORDER BY a."publishedAt" DESC
    """ % (days, source_filter)), (sources or []))
    articles = cur.fetchall()
    if limit:
        articles = articles[:limit]

    print(f"Articles à traiter : {len(articles)} (cookies EBRA {'OK' if alsace_active else 'ABSENT'})"
          + (f" | sources: {sources}" if sources else ""))

    done = 0
    with_gallery = 0
    errors = 0

    for i, (art_id, link, hero_url, hero_caption) in enumerate(articles, 1):
        try:
            content, image_caption, active, err, images = scf.fetch_article_content(
                link, cookies_dict, alsace_active
            )
            # Le hero est remis en tête par sync_article_images (source DB) ;
            # on ne garde ici que la galerie.
            if images:
                changed = scf.sync_article_images(conn, art_id, images, hero_url, hero_caption or image_caption)
                conn.commit()
                if changed:
                    done += 1
                    with_gallery += 1
            print(f"  [{i}/{len(articles)}] {'OK' if images else '—'} | {link[:55]}")
        except Exception as e:
            errors += 1
            print(f"  [{i}/{len(articles)}] ERR {link[:55]} :: {str(e)[:80]}")
        time.sleep(random.uniform(0.8, 1.5))

    cur.execute('SELECT COUNT(*) FROM "ArticleImage" WHERE source = %s', ('gallery',))
    total_gallery = cur.fetchone()[0]
    print(f"\n=== Résumé : {done} traités, {with_gallery} avec galerie, {errors} erreurs ===")
    print(f"Total images gallery en base : {total_gallery}")


if __name__ == "__main__":
    main()
