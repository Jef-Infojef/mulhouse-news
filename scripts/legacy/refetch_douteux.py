import re
import psycopg2
from dotenv import load_dotenv
from curl_cffi import requests
from scrape_content_full import fetch_article_content, sync_article_images, get_db_connection, get_app_config

load_dotenv(".env.local")
load_dotenv(".env")

def build_cookies(conn):
    db_session = get_app_config(conn, "EBRA_SESSION")
    db_poool = get_app_config(conn, "EBRA_POOOL")
    if not db_session:
        print("[!] Pas de EBRA_SESSION en DB - abandon")
        return None, False
    s_val = db_session.strip().replace('"', "").replace("'", "")
    if "2=" in s_val:
        s_val = s_val[s_val.find("2="):].split(";")[0].strip()
    p_val = db_poool.strip().replace('"', "").replace("'", "") if db_poool else "9aab6ee3-fda6-43fc-a90e-29de3c73d8f7"
    if "_poool=" in p_val:
        p_val = p_val.split("_poool=")[1].split(";")[0]
    uuid_match = re.search(r'[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}', p_val)
    if uuid_match:
        p_val = uuid_match.group(0)
    cookies = {".XCONNECT_SESSION": s_val, ".XCONNECTKeepAlive": "2=1", ".XCONNECT": "2=1", "_poool": p_val}
    test = requests.get("https://www.lalsace.fr/", cookies=cookies, impersonate="chrome110", timeout=15)
    connected = any(x in test.text for x in ["Se déconnecter", "Mon compte"])
    return cookies, connected

def main():
    conn = get_db_connection()
    cookies, connected = build_cookies(conn)
    print(f"[*] Session premium: {'OUI' if connected else 'NON'}")

    cur = conn.cursor()
    cur.execute("""
        SELECT id, title, link
        FROM "Article"
        WHERE (content IS NULL OR LENGTH(content) < 500)
          AND link LIKE '%lalsace.fr%'
          AND "publishedAt" >= '2026-08-01'
        ORDER BY "publishedAt" ASC
    """)
    articles = cur.fetchall()
    print(f"[*] Articles douteux à retraiter: {len(articles)}\n")

    ok = 0
    failed = 0
    lens = []

    for i, (art_id, title, link) in enumerate(articles, 1):
        cur.execute('SELECT "imageUrl", "imageCaption" FROM "Article" WHERE id = %s', (art_id,))
        img_url, img_caption = cur.fetchone()

        content, image_caption, active, err, images = fetch_article_content(link, cookies, connected)

        if content and len(content) >= 500:
            cur.execute('UPDATE "Article" SET content = %s WHERE id = %s', (content, art_id))
            sync_article_images(conn, art_id, images, img_url, img_caption or image_caption)
            if image_caption:
                cur.execute('UPDATE "Article" SET "imageCaption" = %s WHERE id = %s', (image_caption, art_id))
            conn.commit()
            ok += 1
            lens.append(len(content))
            print(f"[OK] {len(content):5d} chars | {title[:60]}")
        else:
            failed += 1
            print(f"[!!] {'trop court' if content else 'FAILED'} | {title[:60]} | {err}")

    print(f"\n=== RÉSULTAT ===")
    print(f"Complets: {ok} | échecs: {failed}")
    if lens:
        print(f"Longueurs: min={min(lens)}, max={max(lens)}, moy={sum(lens)//len(lens)}")
    conn.close()

if __name__ == "__main__":
    main()
