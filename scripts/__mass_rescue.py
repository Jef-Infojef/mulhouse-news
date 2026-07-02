import sys, os, psycopg2, time, random
sys.path.append(os.getcwd())
import scripts.scrape_content_full as s
from dotenv import load_dotenv
load_dotenv(".env.local")
url = os.environ["DATABASE_URL"].replace("?pgbouncer=true", "").replace("&pgbouncer=true", "")

conn = psycopg2.connect(url)
cur = conn.cursor()

cur.execute("""
  SELECT id, title, link, source FROM "Article"
  WHERE (content IS NULL OR content = '')
    AND "publishedAt" >= '2025-01-01'
  ORDER BY "publishedAt" DESC
""")
articles = cur.fetchall()
print(f"Rescrape massif de {len(articles)} articles...\n")

cookies = {}
results = {}
ok_total = 0
for i, (aid, title, link, source) in enumerate(articles, 1):
    if source not in results:
        results[source] = {"ok": 0, "fail": 0, "total": 0}
    results[source]["total"] += 1
    
    print(f"  [{i}/{len(articles)}] {source}: {title[:35]}...", end=" ", flush=True)
    time.sleep(random.uniform(0.3, 0.6))
    content, active, err = s.fetch_article_content(link, cookies, True)
    if content and len(content) >= 80:
        cur.execute('UPDATE "Article" SET content = %s WHERE id = %s', (content.replace('\x00', ''), aid))
        conn.commit()
        ok_total += 1
        results[source]["ok"] += 1
        print(f"OK {len(content)}c")
    else:
        results[source]["fail"] += 1
        print(f"FAIL {err}")

print(f"\n=== RESULTATS ===")
for src, r in sorted(results.items(), key=lambda x: -x[1]["total"]):
    print(f"  {src:25s}: {r['ok']}/{r['total']} ({r['ok']*100//r['total'] if r['total'] else 0}%)")

print(f"\nTotal: {ok_total}/{len(articles)} OK")

# Check remaining
cur.execute("SELECT COUNT(*) FROM \"Article\" WHERE (content IS NULL OR content = '') AND \"publishedAt\" >= '2025-01-01'")
rest = cur.fetchone()[0]
print(f"Il reste: {rest} vides")
conn.close()
