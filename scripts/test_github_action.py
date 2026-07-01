import os, sys, requests
import psycopg2
from bs4 import BeautifulSoup

errors = []

print("=== Test Connexion Base de Données ===")
db_url = os.environ.get("DATABASE_URL")
if not db_url:
    errors.append("DATABASE_URL manquante")
    print("❌ DATABASE_URL non définie")
else:
    try:
        clean_url = db_url.replace("?pgbouncer=true", "").replace("&pgbouncer=true", "")
        conn = psycopg2.connect(clean_url)
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM \"Article\"")
        count = cur.fetchone()[0]
        print(f"✅ Connexion OK — {count} articles en base")
        cur.close()
        conn.close()
    except Exception as e:
        errors.append(f"Connexion DB échouée : {e}")
        print(f"❌ {e}")

print("\n=== Test ALSACE_COOKIES ===")
cookies_str = os.environ.get("ALSACE_COOKIES")
if not cookies_str:
    errors.append("ALSACE_COOKIES manquante")
    print("❌ ALSACE_COOKIES non définie")
else:
    try:
        cookies = {}
        for part in cookies_str.split(";"):
            if "=" in part:
                k, v = part.strip().split("=", 1)
                cookies[k] = v
        resp = requests.get(
            "https://www.lalsace.fr/",
            cookies=cookies,
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=15
        )
        if resp.status_code == 200 and "lalsace" in resp.text.lower():
            print(f"✅ Cookies OK — status {resp.status_code}")
        else:
            errors.append(f"Réponse inattendue: status {resp.status_code}")
            print(f"❌ Status {resp.status_code}")
    except Exception as e:
        errors.append(f"Test cookies échoué : {e}")
        print(f"❌ {e}")

print("\n=== Test curl_cffi ===")
try:
    from curl_cffi import requests as curl_requests
    resp = curl_requests.get("https://www.lalsace.fr/", impersonate="chrome", timeout=15)
    print(f"✅ curl_cffi OK — status {resp.status_code}")
except Exception as e:
    errors.append(f"curl_cffi échoué : {e}")
    print(f"❌ {e}")

print("\n=== Résumé ===")
if errors:
    print(f"❌ {len(errors)} erreur(s) :")
    for e in errors:
        print(f"   - {e}")
    sys.exit(1)
else:
    print("✅ Tous les tests sont passés")
