import sys
import os
sys.path.append(os.getcwd())
import scripts.scrape_content_full as s
import psycopg2

def fix_january_2026():
    conn = s.get_db_connection()
    cur = conn.cursor()
    
    # On cherche les articles Alsace de JANVIER 2026 avec un contenu court ou nul
    query = """
        SELECT id, title, link 
        FROM "Article" 
        WHERE (content IS NULL OR LENGTH(content) < 500)
          AND (source IN ('L''Alsace', 'lalsace.fr'))
          AND "publishedAt" >= '2026-01-01'
          AND "publishedAt" < '2026-02-01'
    """
    cur.execute(query)
    articles = cur.fetchall()
    print(f"Reparation de {len(articles)} articles Alsace pour Janvier 2026...")
    
    # On charge les cookies depuis la DB
    db_session = s.get_app_config(conn, "EBRA_SESSION")
    db_poool = s.get_app_config(conn, "EBRA_POOOL")
    cookies = {}
    if db_session:
        s_val = db_session.strip().replace('"', '').replace("'", "")
        if "2=" in s_val: s_val = s_val[s_val.find("2="):].split(";")[0]
        p_val = db_poool.strip().replace('"', '').replace("'", "") if db_poool else "9aab6ee3-fda6-43fc-a90e-29de3c73d8f7"
        if "_poool=" in p_val: p_val = p_val.split("_poool=")[1].split(";")[0]
        cookies = {".XCONNECT_SESSION": s_val, ".XCONNECTKeepAlive": "2=1", ".XCONNECT": "2=1", "_poool": p_val}

    for aid, title, link in articles:
        print(f"  [*] Traitement : {title[:50]}...")
        content, active, err = s.fetch_article_content(link, cookies, True)
        if content and len(content) > 500:
            clean_content = content.replace('\x00', '')
            cur.execute('UPDATE "Article" SET content = %s WHERE id = %s', (clean_content, aid))
            conn.commit()
            print(f"    [✅] Réparé : {len(clean_content)} chars")
        elif content:
            print(f"    [➖] Contenu toujours court ({len(content)} chars), probablement normal (vidéo/brève).")
        else:
            print(f"    [❌] Échec : {err}")
    
    conn.close()

if __name__ == "__main__":
    fix_january_2026()
