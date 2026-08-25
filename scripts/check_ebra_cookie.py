"""
Verifie quotidiennement que le cookie EBRA debloque encore le contenu premium.

Approche : on prend un article premium connu, on le fetch avec le cookie EBRA
(bdd AppConfig) puis sans cookie. Si le texte rendu avec cookie est a peu pres
le meme que sans cookie, la session ne debloque plus rien -> cookie invalide.

Sortie : exit 0 si cookie OK, exit 1 sinon (le workflow notifie Telegram).
"""

import os
import re

import psycopg2
from bs4 import BeautifulSoup
from curl_cffi import requests

import convex_client

# Articles premium dont le contenu fluctue fortement entre version gratuite
# (chapo seul) et version abonne (corps complet). Mettre a jour si l'un
# d'eux disparait du site.
TEST_URLS = [
    "https://www.lalsace.fr/economie/2026/08/04/plein-ciel-l-acquisition-des-tours-en-vue-de-leur-demolition-est-declaree-d-utilite-publique",
    "https://www.lalsace.fr/tour-de-france/2026/06/17/col-du-haag-ballon-d-alsace-on-a-teste-le-col-moine-du-grand-depart",
    "https://www.lalsace.fr/economie/2026/07/23/data-center-a-petit-landau-le-projet-entre-en-zone-de-reflexion",
]

# Ecart minimum (caracteres) entre version abonne et version gratuite pour
# considerer que la session fonctionne encore.
MIN_DELTA = 500

# Backend : Convex (cloud) si USE_CONVEX=1 ou CONVEX_DEPLOY_KEY définie.
USE_CONVEX = convex_client.use_convex()


def get_db_connection():
    url = os.environ.get("DATABASE_URL", "")
    if not url:
        raise SystemExit("DATABASE_URL manquant")
    clean = url.replace("?pgbouncer=true", "").replace("&pgbouncer=true", "")
    return psycopg2.connect(clean)


def get_config(cur, key):
    if USE_CONVEX:
        return convex_client.get_app_config(key)
    cur.execute('SELECT value FROM "AppConfig" WHERE key = %s', (key,))
    row = cur.fetchone()
    return row[0] if row else None


def build_cookies(session_raw, poool_raw):
    s_val = (session_raw or "").strip().replace('"', "").replace("'", "")
    if "2=" in s_val:
        s_val = s_val[s_val.find("2="):].split(";")[0].strip()

    p_val = (poool_raw or "").strip().replace('"', "").replace("'", "")
    if "_poool=" in p_val:
        p_val = p_val.split("_poool=")[1].split(";")[0]
    m = re.search(
        r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-"
        r"[0-9a-fA-F]{4}-[0-9a-fA-F]{12}",
        p_val,
    )
    if m:
        p_val = m.group(0)

    return {
        ".XCONNECT_SESSION": s_val,
        ".XCONNECTKeepAlive": "2=1",
        ".XCONNECT": "2=1",
        "_poool": p_val,
    }


def fetch_page(url, cookies):
    try:
        resp = requests.get(
            url, cookies=cookies, impersonate="chrome120", timeout=30, allow_redirects=True
        )
    except Exception as err:
        if "CertificateVerifyError" in str(err) or "SSL" in str(err):
            resp = requests.get(
                url,
                cookies=cookies,
                impersonate="chrome120",
                timeout=30,
                allow_redirects=True,
                verify=False,
            )
        else:
            raise
    return resp


def extract_body_len(html):
    """Longueur du texte que le scraper EBRA utilise (chapeau + textComponent)."""
    soup = BeautifulSoup(html, "html.parser")
    parts = []
    chapo = soup.find(class_="chapo") or soup.find(class_="article__chapo")
    if chapo:
        parts.append(chapo.get_text().strip())
    inner = soup.find(class_="innerContent")
    if inner:
        parts.append(inner.get_text(strip=True))
    for block in soup.find_all("div", class_="textComponent"):
        txt = block.get_text("\n", strip=True)
        if len(txt) > 10:
            parts.append(txt)
    return len("\n\n".join(dict.fromkeys(parts)))


def main():
    conn = None if USE_CONVEX else get_db_connection()
    cur = conn.cursor() if conn else None
    session_raw = get_config(cur, "EBRA_SESSION")
    poool_raw = get_config(cur, "EBRA_POOOL")
    if conn:
        conn.close()

    if not session_raw:
        print("❌ EBRA_SESSION absent de AppConfig -> cookie indisponible")
        raise SystemExit(1)

    cookies = build_cookies(session_raw, poool_raw)

    tested = None
    with_len = 0
    without_len = 0
    for url in TEST_URLS:
        try:
            resp_ok = fetch_page(url, cookies)
            if resp_ok.status_code != 200:
                print(f"[premium abonne] HTTP {resp_ok.status_code} pour {url} (ignore)")
                continue
            resp_no = fetch_page(url, None)
            if resp_no.status_code != 200:
                print(f"[sans cookie]    HTTP {resp_no.status_code} pour {url} (ignore)")
                continue
            with_len = extract_body_len(resp_ok.text)
            without_len = extract_body_len(resp_no.text)
            tested = url
            break
        except Exception as err:
            print(f"[!] erreur fetch {url}: {err} (ignore)")
            continue

    if tested is None:
        print("⚠️ Aucun article de test joignable, test non concluant (aucune alerte)")
        raise SystemExit(0)

    delta = with_len - without_len
    print("\n=== CONTROLE COOKIE EBRA ===")
    print(f"Article        : {tested}")
    print(f"Avec cookie    : {with_len} chars")
    print(f"Sans cookie    : {without_len} chars")
    print(f"Ecart          : {delta} chars (seuil {MIN_DELTA})")

    if delta >= MIN_DELTA:
        print("✅ Cookie OK : la session debloque bien le contenu premium.")
        raise SystemExit(0)

    print("❌ Cookie KO : l'ecart est trop faible, le contenu premium ne")
    print("   se debloque plus avec cette session.")
    print("   -> renouveler EBRA_SESSION / EBRA_POOOL dans AppConfig,"
          " et le secret ALSACE_COOKIES.")
    raise SystemExit(1)


if __name__ == "__main__":
    main()