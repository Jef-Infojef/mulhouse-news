import os, psycopg2
from dotenv import load_dotenv
load_dotenv(".env.local")
url = os.environ["DATABASE_URL"].replace("?pgbouncer=true", "").replace("&pgbouncer=true", "")
conn = psycopg2.connect(url)
cur = conn.cursor()

cur.execute("""
  SELECT source, COUNT(*) FROM "Article"
  WHERE (content IS NULL OR content = '')
    AND "publishedAt" >= '2025-01-01'
  GROUP BY source
  ORDER BY COUNT(*) DESC
  LIMIT 20
""")
print("Top sources vides (>=2025):\n")
for s, c in cur.fetchall():
    print(f"  {s or 'NULL'}: {c}")

cur.execute("SELECT COUNT(*) FROM \"Article\" WHERE (content IS NULL OR content = '') AND \"publishedAt\" >= '2025-01-01'")
print(f"\nTotal: {cur.fetchone()[0]}")

# Also check sources easy to add handlers for
cur.execute("""
  SELECT source, link FROM "Article"
  WHERE (content IS NULL OR content = '')
    AND "publishedAt" >= '2025-01-01'
  ORDER BY "publishedAt" DESC LIMIT 20
""")
print("\nDerniers articles vides par source:")
for s, l in cur.fetchall():
    domain = l.split('/')[2] if '//' in l else '?'
    print(f"  {s}: {domain}")

conn.close()
