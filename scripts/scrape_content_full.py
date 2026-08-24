import os
import sys
import argparse
import psycopg2
from bs4 import BeautifulSoup
import json
import re
import time
import random
import subprocess
import html as htmllib
from curl_cffi import requests
from dotenv import load_dotenv
from datetime import datetime, timedelta
from scrape_utils import (
    extract_image_caption,
    extract_article_images,
    fetch_page_caption,
    parse_mplusinfo_article,
    _absolutize_media_url,
    _normalize_image_path,
)
import convex_client

SKIP_PHRASES = ['cookie', 'abonnez', 'newsletter', 'mentions légales', 'politique de confidentialité', 'publicité']

GRDC_SKIP_FRAGMENTS = ["lire dans l'application", "ajoutez-nous", "favoris", "newsletter"]


def fetch_grdc_content(page_text, target_url, cookies_dict):
    """Contenu complet L'Alsace via l'API interne /services/grdc/detail.

    Le texte des articles (payants y compris) n'est pas dans le HTML de la
    page : il est livré par l'API GRDC appelée en JS, avec pour clé
    dataLayer[0].dimension38. Retourne (content, images_gallery) ou (None, []).
    """
    if "lalsace.fr" not in target_url:
        return None, []
    m = re.search(r"['\"]dimension38['\"]\s*:\s*['\"]([0-9a-fA-F-]{8,})['\"]", page_text)
    if not m:
        return None, []
    key = m.group(1)
    try:
        host = target_url.split("/")[2]
        api = f"https://{host}/services/grdc/detail?key={key}"
        time.sleep(random.uniform(0.1, 0.2))
        resp = requests.get(api, cookies=cookies_dict, impersonate="chrome120", timeout=30)
        if resp.status_code != 200:
            return None, []
        data = resp.json()
        html = data.get("html") if isinstance(data, dict) else None
        if not html:
            return None, []
        soup = BeautifulSoup(html, "html.parser")
        for junk in soup.select(".fullDetailActions, .illustration"):
            junk.decompose()

        images = []
        seen_paths = set()
        for img in soup.find_all("img"):
            src = img.get("src") or img.get("data-src") or ""
            src = _absolutize_media_url(target_url, src) if src else None
            if not src:
                continue
            norm = _normalize_image_path(src)
            if norm in seen_paths:
                continue
            seen_paths.add(norm)
            caption = None
            figcap = img.find_parent("figure")
            if figcap:
                fc = figcap.find("figcaption")
                if fc:
                    caption = fc.get_text(" ", strip=True).strip() or None
            images.append({"url": src, "caption": caption, "source": "gallery"})

        blocks = []
        body = soup.select_one(".retrievedBodyContent")
        candidates = body.find_all(["div", "p", "h2", "h3", "h4", "figure"], recursive=True) if body else []
        for el in candidates:
            txt = el.get_text("\n", strip=True)
            if len(txt) > 20 and not any(s in txt.lower() for s in GRDC_SKIP_FRAGMENTS):
                blocks.append(txt)
        if not blocks:
            for el in soup.find_all(["p", "h2", "h3"], recursive=True):
                txt = el.get_text("\n", strip=True)
                if len(txt) > 20:
                    blocks.append(txt)
        content = "\n\n".join(dict.fromkeys(blocks))
        if len(content) < 400:
            return None, []
        return content, images
    except Exception:
        return None, []

# Charger l'environnement
load_dotenv(".envenv")
load_dotenv(".env.local")
load_dotenv(".env")

# Console Windows : éviter les UnicodeEncodeError sur emojis/accents
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

DATABASE_URL = os.environ.get("DATABASE_URL")

# Backend : Convex (cloud) si USE_CONVEX=1 ou CONVEX_DEPLOY_KEY définie.
USE_CONVEX = convex_client.use_convex()
if USE_CONVEX:
    print("[*] Backend: Convex (cloud)")
else:
    print("[*] Backend: Supabase (psycopg2)")

def get_db_connection():
    if not DATABASE_URL:
        raise ValueError("DATABASE_URL is not set")
    clean_url = DATABASE_URL.replace("?pgbouncer=true", "").replace("&pgbouncer=true", "")
    return psycopg2.connect(clean_url)


def list_missing_content_via_pages(limit: int) -> list[dict]:
    """Articles lalsace.fr au contenu manquant/court.

    1. Query dédiée `getArticlesMissingContentAll` (métadonnées seules, un
       appel HTTP) — c'est le chemin rapide.
    2. Repli : pagination `getArticlesPage` (CONTENT inclus, lourd). Un log
       par page, sinon le terminal reste muet jusqu'à la 50ᵉ (~25 k docs).
    """
    print("[*] Recherche des articles lalsace.fr sans texte…", flush=True)
    try:
        found = convex_client.get_articles_missing_content_all(
            limit=limit or 300,
            max_pages=200,
        )
        if found:
            print(f"[*] {len(found)} candidats (query dédiée, sans télécharger les textes)", flush=True)
            return found
        print("[*] Query dédiée : 0 candidat, scan page par page pour confirmer", flush=True)
    except Exception as exc:
        print(f"[!] Query dédiée indisponible ({exc}) — scan page par page", flush=True)

    rows: list[dict] = []
    cursor: str | None = None
    page = 0
    while True:
        page += 1
        print(f"[*] Scan Convex page {page} (~500 docs, textes complets)…", flush=True)
        res = convex_client._call(
            "news_bridge:getArticlesPage",
            {"cursor": cursor, "limit": 500},
            mutation=False,
        )
        for a in res["articles"]:
            link = a.get("link") or ""
            content = a.get("content")
            if "lalsace.fr" not in link:
                continue
            if content and len(content) >= 150:
                continue
            rows.append({
                "link": link,
                "title": a.get("title") or "",
                "description": a.get("description"),
                "imageUrl": a.get("imageUrl"),
                "imageCaption": None,
                "supabaseId": a.get("id"),
            })
            if limit and len(rows) >= limit:
                print(f"[*] {len(rows)} candidats trouvés (limite atteinte)", flush=True)
                return rows
        print(f"[*] … page {page} ok, {len(rows)} sans contenu pour l'instant", flush=True)
        if res.get("isDone") or not res.get("cursor"):
            print(f"[*] {len(rows)} articles lalsace.fr sans contenu (sur {page} pages)", flush=True)
            return rows
        cursor = res["cursor"]

def get_app_config(conn, key):
    if USE_CONVEX:
        return convex_client.get_app_config(key)
    try:
        with conn.cursor() as cur:
            cur.execute('SELECT value FROM "AppConfig" WHERE key = %s', (key,))
            row = cur.fetchone()
            return row[0] if row else None
    except:
        return None


def load_ebra_cookies(conn=None) -> tuple[dict, bool]:
    """Session EBRA (Poool) pour GRDC. Retourne (cookies, session_connue)."""
    cookies_dict: dict = {}
    db_session = get_app_config(conn, "EBRA_SESSION")
    db_poool = get_app_config(conn, "EBRA_POOOL")
    if db_session:
        s_val = db_session.strip().replace('"', "").replace("'", "")
        if "2=" in s_val:
            s_val = s_val[s_val.find("2="):].split(";")[0].strip()
        p_val = db_poool.strip().replace('"', "").replace("'", "") if db_poool else "9aab6ee3-fda6-43fc-a90e-29de3c73d8f7"
        if "_poool=" in p_val:
            p_val = p_val.split("_poool=")[1].split(";")[0]
        uuid_match = re.search(
            r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}", p_val
        )
        if uuid_match:
            p_val = uuid_match.group(0)
        cookies_dict = {
            ".XCONNECT_SESSION": s_val,
            ".XCONNECTKeepAlive": "2=1",
            ".XCONNECT": "2=1",
            "_poool": p_val,
        }
        return cookies_dict, True
    fallback = get_app_config(conn, "EBRA_COOKIE") or os.environ.get("ALSACE_COOKIES")
    if fallback:
        clean = fallback.strip().replace('"', "").replace("'", "")
        if ";" in clean and "=" in clean:
            for item in clean.split(";"):
                if "=" in item:
                    k, v = item.split("=", 1)
                    cookies_dict[k.strip()] = v.strip()
        else:
            session_val = clean[clean.find("2="):].split(";")[0] if "2=" in clean else clean
            cookies_dict = {
                ".XCONNECT_SESSION": session_val,
                ".XCONNECTKeepAlive": "2=1",
                ".XCONNECT": "2=1",
                "_poool": "9aab6ee3-fda6-43fc-a90e-29de3c73d8f7",
            }
        return cookies_dict, True
    return cookies_dict, False

RETRY_COOLDOWN_KEY = "SCRAPE_CONTENT_RETRY_COOLDOWNS"
# Seuil de la query getArticlesShortContent : en dessous, l'article revient
# à chaque cron. Un chapo / une description de 200 chars ne doit pas relancer
# un HTTP toutes les 15 min.
FULL_CONTENT_MIN = 500
SAVE_CONTENT_MIN = 150
# Tentative 1 → 6 h, 2 → 12 h, 3 → 24 h, 4 → 48 h, 5+ → 7 j
BACKOFF_HOURS = (6, 12, 24, 48, 168)
# 404 / article intrinsèquement court : pas la peine de retester avant 7 j
PERMANENT_BACKOFF_HOURS = BACKOFF_HOURS[-1]


def get_retry_cooldowns(conn):
    """Cooldowns d'échec par article.

    Format actuel : {id: {until, fails, reason}}.
    Ancien format (string ISO) encore lu.
    """
    raw = get_app_config(conn, RETRY_COOLDOWN_KEY)
    if not raw:
        return {}
    try:
        data = json.loads(raw)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _parse_cooldown_entry(raw):
    """Retourne (until: datetime | None, fails: int)."""
    if isinstance(raw, str):
        try:
            return datetime.fromisoformat(raw), 1
        except ValueError:
            return None, 1
    if isinstance(raw, dict):
        until = None
        iso = raw.get("until")
        if iso:
            try:
                until = datetime.fromisoformat(iso)
            except ValueError:
                until = None
        try:
            fails = max(int(raw.get("fails") or 1), 1)
        except (TypeError, ValueError):
            fails = 1
        return until, fails
    return None, 1


def _backoff_hours(fails: int, reason: str) -> int:
    if reason in ("http_404", "http_410", "short"):
        return PERMANENT_BACKOFF_HOURS
    idx = min(max(fails, 1) - 1, len(BACKOFF_HOURS) - 1)
    return BACKOFF_HOURS[idx]


def cooldown_active(cooldowns, art_id):
    """True si l'article est encore en cooldown (ne pas refetch)."""
    until, _ = _parse_cooldown_entry(cooldowns.get(art_id))
    return bool(until and datetime.now() < until)


def mark_retry_cooldown(cooldowns, art_id, reason: str, *, increment: bool = True):
    """Enregistre un backoff. Conservé le compteur d'échecs après expiration."""
    _, prev_fails = _parse_cooldown_entry(cooldowns.get(art_id))
    if increment and art_id in cooldowns:
        fails = prev_fails + 1
    else:
        fails = 1
    hours = _backoff_hours(fails, reason)
    until = datetime.now() + timedelta(hours=hours)
    cooldowns[art_id] = {
        "until": until.isoformat(),
        "fails": fails,
        "reason": reason,
    }
    return until, fails, hours


def prune_retry_cooldowns(cooldowns):
    """Droppe les entrées expirées depuis plus de 7 j (articles hors fenêtre)."""
    cutoff = datetime.now() - timedelta(days=7)
    drop = []
    for key, raw in cooldowns.items():
        until, _ = _parse_cooldown_entry(raw)
        if until and until < cutoff:
            drop.append(key)
    for key in drop:
        del cooldowns[key]


def persist_retry_cooldowns(conn, cooldowns):
    try:
        payload = json.dumps(cooldowns)
        if USE_CONVEX:
            convex_client.set_app_config(RETRY_COOLDOWN_KEY, payload)
        else:
            with conn.cursor() as cur:
                cur.execute(
                    'INSERT INTO "AppConfig" (key, value, "updatedAt") VALUES (%s, %s, NOW()) '
                    'ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value, "updatedAt" = NOW()',
                    (RETRY_COOLDOWN_KEY, payload),
                )
            conn.commit()
    except Exception as e:
        print(f"[!] Cooldowns de retry non persistés : {e}")

def sync_article_images(conn, article_id, images, image_url, image_caption):
    """Enregistre toutes les images d'un article dans ArticleImage.

    L'image hero (imageUrl BDD) est toujours position 0. Les autres images
    sont ajoutées/actualisées par URL, sans doublon.
    Convex : article_id = UUID Supabase (supabaseId) ; upsert par (articleId, url).
    """
    if not images and not image_url:
        return False

    if USE_CONVEX:
        all_images = list(images)
        if image_url:
            hero = {"url": image_url, "caption": image_caption, "source": "hero"}
            all_images = [hero] + [
                dict(i, source="gallery")
                for i in all_images
                if i.get("url") and not _same_img(i["url"], image_url)
            ]
        rows = []
        for position, img in enumerate(all_images):
            url = (img.get("url") or "").strip()
            if not url:
                continue
            rows.append(
                {
                    "articleId": article_id,
                    "url": url,
                    "caption": img.get("caption"),
                    "position": position,
                    "source": img.get("source") or ("hero" if position == 0 else "gallery"),
                }
            )
        if rows:
            convex_client.upsert_article_images(rows)
        return True

    changed = False

    with conn.cursor() as cur:
        cur.execute(
            'SELECT url, caption, "source", position FROM "ArticleImage" WHERE "articleId" = %s',
            (article_id,),
        )
        existing = {(r[0], r[1], r[2], r[3]) for r in cur.fetchall()}

        if image_url:
            hero = {"url": image_url, "caption": image_caption, "source": "hero"}
            images = [hero] + [
                dict(i, source="gallery")
                for i in images
                if i.get("url") and not _same_img(i["url"], image_url)
            ]

        for position, img in enumerate(images):
            url = (img.get("url") or "").strip()
            if not url:
                continue
            caption = img.get("caption")
            source = img.get("source") or ("hero" if position == 0 else "gallery")
            row = (url, caption, source, position)
            if row in existing:
                continue
            if (url,) in {(u,) for u, _, _, _ in existing}:
                cur.execute(
                    'UPDATE "ArticleImage" SET caption = %s, "source" = %s, position = %s WHERE "articleId" = %s AND url = %s',
                    (caption, source, position, article_id, url),
                )
            else:
                cur.execute(
                    'INSERT INTO "ArticleImage" (id, "articleId", url, caption, position, source, "createdAt") VALUES (gen_random_uuid(), %s, %s, %s, %s, %s, NOW())',
                    (article_id, url, caption, position, source),
                )
            changed = True

    return changed

def _norm_img(url):
    """Normalise une URL d'image pour comparer les variantes d'un même cliché.

    La clé = UUID du dossier `/images/<UUID>/` + identifiant numérique du
    fichier. L'UUID distingue deux clichés différents ; l'ID numérique
    distingue les images dans un même dossier. Les variantes de résolution
    (FB1200/NW_raw) partagent UUID + ID → même clé ; deux photos distinctes
    n'ont jamais le même couple.
    """
    if not url:
        return ""
    path = url.split("?")[0]
    low = path.lower()
    m = re.search(r"/images/([0-9a-f-]{8,36})/", low)
    folder = m.group(1) if m else ""
    m2 = re.search(r"-(\d{5,})\.(webp|jpg|jpeg|png|gif)$", low)
    file_id = m2.group(1) if m2 else ""
    name = re.sub(r"(-\d{2,}){1,3}\.(webp|jpg|jpeg|png|gif)$", "", low.split("/")[-1])
    name = re.sub(r"\.(webp|jpg|jpeg|png|gif)$", "", name)
    return (folder, file_id, name)


def _same_img(url_a, url_b):
    """True si deux URLs d'image désignent le même cliché (variantes de résolution)."""
    if not url_a or not url_b:
        return False
    fa, ia, na = _norm_img(url_a)
    fb, ib, nb = _norm_img(url_b)
    if fa and fb:
        if ia and ib:
            return fa == fb and ia == ib
        return fa == fb and na == nb
    return na == nb

def fetch_article_content(url, cookies_dict, alsace_cookies_active):
    """Récupère le contenu complet selon la source."""
    try:
        # Fallback intelligent pour le groupe EBRA (DNA, Est Républicain, etc.)
        # Si on a des cookies L'Alsace, on tente de transformer l'URL DNA/EstRep en L'Alsace
        target_url = url
        if alsace_cookies_active and ("dna.fr" in url or "estrepublicain.fr" in url or "vosgesmatin.fr" in url):
            target_url = url.replace("www.dna.fr", "www.lalsace.fr").replace("www.estrepublicain.fr", "www.lalsace.fr").replace("www.vosgesmatin.fr", "www.lalsace.fr")
            if target_url != url:
                print(f"    [🔄] Test Fallback L'Alsace pour : {url[:40]}...")

        time.sleep(random.uniform(0.1, 0.25))
        
        try:
            resp = requests.get(target_url, cookies=cookies_dict, impersonate="chrome120", timeout=30, allow_redirects=True)
        except Exception as ssl_err:
            if "CertificateVerifyError" in str(ssl_err) or "SSL" in str(ssl_err):
                resp = requests.get(target_url, cookies=cookies_dict, impersonate="chrome120", timeout=30, allow_redirects=True, verify=False)
            else:
                raise ssl_err

        # Si le fallback L'Alsace échoue (404), on tente l'URL originale sans cookies (pour les gratuits)
        if resp.status_code == 404 and target_url != url:
            try:
                resp = requests.get(url, impersonate="chrome120", timeout=20, allow_redirects=True)
            except Exception as ssl_err:
                if "CertificateVerifyError" in str(ssl_err) or "SSL" in str(ssl_err):
                    resp = requests.get(url, impersonate="chrome120", timeout=20, allow_redirects=True, verify=False)
                else:
                    raise ssl_err
            
        if resp.status_code != 200:
            return None, None, True, f"HTTP {resp.status_code}", []

        page_text = resp.text
        is_connected = any(x in page_text for x in ["Se déconnecter", "Mon compte", "Mon profil", "suscriber", "premium", "Abonné"])
        
        # Si c'était un article L'Alsace (ou transformé en L'Alsace) et qu'on n'est pas connecté
        if not is_connected and alsace_cookies_active and "lalsace.fr" in target_url:
            # On continue quand même pour tenter de choper le chapo ou LD+JSON
            print(f"    [!] Mode non-abonné pour : {target_url[:40]}")

        soup = BeautifulSoup(page_text, 'html.parser')
        image_caption = extract_image_caption(soup, target_url)
        images = extract_article_images(soup, target_url)
        text_parts = []

        # LD+JSON articleBody pour toute source (20 Minutes, Foot National, etc.)
        for script in soup.find_all('script', type='application/ld+json'):
            try:
                raw = script.string.strip()
                data = json.loads(raw)
                items = data.get('@graph', data) if isinstance(data, dict) else data
                if isinstance(items, dict): items = [items]
                for item in items:
                    if isinstance(item, dict) and item.get('articleBody'):
                        body = item['articleBody'].strip()
                        if len(body) > 100:
                            return body, image_caption, True, None, images
            except: pass

        # Logique EBRA (L'Alsace, DNA...)
        if any(x in target_url for x in ["lalsace.fr", "dna.fr", "estrepublicain.fr", "vosgesmatin.fr"]):
            # ... [Logique EBRA existante conservée] ...
            is_video_page = "/videos/" in target_url

            # 1) Contenu complet via l'API GRDC : le texte des articles payants
            #    n'est pas dans le HTML de la page (rendu JS), GRDC le fournit.
            if "lalsace.fr" in target_url and not is_video_page:
                grdc_content, grdc_images = fetch_grdc_content(page_text, target_url, cookies_dict)
                if grdc_content:
                    if grdc_images:
                        existing = {_normalize_image_path(i["url"]) for i in images}
                        images += [i for i in grdc_images if _normalize_image_path(i["url"]) not in existing]
                    print(f"    [GRDC] Contenu complet ({len(grdc_content)} chars) : {target_url[:45]}...")
                    return grdc_content, image_caption, True, None, images

            # 2) Refus du contenu partiel (session non abonnée) : L'Alsace
            if "lalsace.fr" in target_url and not is_connected and not is_video_page:
                print(f"    [⛔] Contenu partiel refusé (Non connecté) pour : {target_url[:40]}")
                return None, image_caption, False, "Not Connected (Partial content refused)", images

            chapo = soup.find(class_='chapo') or soup.find(class_='article__chapo')
            if chapo: text_parts.append(chapo.get_text().strip())
            
            inner = soup.find(class_='innerContent')
            if inner: text_parts.append(inner.get_text(strip=True))

            if is_connected:
                for block in soup.find_all('div', class_='textComponent'):
                    txt = block.get_text("\n", strip=True)
                    if len(txt) > 10: text_parts.append(txt)
            
            if not text_parts or len("\n".join(text_parts)) < 100:
                for script in soup.find_all('script', type='application/ld+json'):
                    try:
                        raw_json = script.string.strip()
                        raw_json = raw_json.replace('" @', '"@')
                        data = json.loads(raw_json)
                        items = data if isinstance(data, list) else [data]
                        for item in items:
                            if item.get('@type') in ['VideoObject', 'NewsArticle'] and item.get('description'):
                                text_parts.append(item['description'].strip())
                    except: pass
        # Logique JDS (Agenda)
        elif "jds.fr" in url:
            for script in soup.find_all('script', type='application/ld+json'):
                try:
                    data = json.loads(script.string)
                    items = data if isinstance(data, list) else [data]
                    for item in items:
                        if 'description' in item and len(str(item['description'])) > 50:
                            text_parts.append(htmllib.unescape(str(item['description'])))
                            break
                except: pass
                if text_parts: break
            if not text_parts:
                desc_div = soup.find('div', class_='description') or soup.find('div', id='description') or soup.find('div', itemprop='description')
                if desc_div:
                    text_parts.append(desc_div.get_text(separator="\n", strip=True))
        # Logique mplusinfo.fr (Next.js / payload RSC embarqué)
        elif "mplusinfo.fr" in url:
            parsed = parse_mplusinfo_article(soup, url)
            if parsed.get("content") and len(parsed["content"]) > 100:
                text_parts.append(parsed["content"])
            elif parsed.get("description") and len(parsed["description"]) > 30:
                text_parts.append(parsed["description"])
            if parsed.get("image_caption") and not image_caption:
                image_caption = parsed["image_caption"]
        # Logique M+ (Mulhouse Alsace Agglomération)
        elif "mag.mulhouse-alsace.fr" in url:
            content_div = soup.find('div', class_='interne')
            if content_div:
                paras = [p.get_text(' ', strip=True) for p in content_div.find_all('p') if len(p.get_text(strip=True)) > 40]
                if paras:
                    text_parts.append('\n\n'.join(paras))
                else:
                    text_parts.append(content_div.get_text(separator="\n\n", strip=True))
        # Logique Le Figaro
        elif "lefigaro.fr" in url:
            for script in soup.find_all('script', type='application/ld+json'):
                try:
                    data = json.loads(script.string.strip())
                    item = data[0] if isinstance(data, list) else data
                    if item.get('@type') == 'NewsArticle' and 'articleBody' in item:
                        text_parts.append(item['articleBody'])
                        break
                except: pass
            if not text_parts:
                body = soup.find('div', class_='fig-content-body')
                if body:
                    paras = [p.get_text(' ', strip=True) for p in body.find_all('p')
                             if len(p.get_text(strip=True)) > 40
                             and not any(s in p.get_text(strip=True).lower() for s in SKIP_PHRASES)]
                    if paras:
                        text_parts.append('\n\n'.join(paras))
        # Logique Les Echos
        elif "lesechos.fr" in url:
            article = soup.find('article')
            if article:
                paras = [p.get_text(' ', strip=True) for p in article.find_all('p')
                         if len(p.get_text(strip=True)) > 40
                         and not any(s in p.get_text(strip=True).lower() for s in SKIP_PHRASES)]
                if paras:
                    text_parts.append('\n\n'.join(paras))
        # Logique Le Trois (Elementor - contenu dans divs)
        if not text_parts and "letrois.info" in url:
            article = soup.find('article')
            if article:
                all_divs = article.find_all('div')
                big_texts = [d.get_text(' ', strip=True) for d in all_divs if len(d.get_text(' ', strip=True)) > 150]
                if big_texts:
                    text_parts.append('\n\n'.join(big_texts))
        # Logique Air Journal
        if not text_parts and "air-journal.fr" in url:
            content = soup.find('div', class_='post-content')
            if content:
                paras = content.find_all('p')
                valid = [p.get_text(' ', strip=True) for p in paras if len(p.get_text(strip=True)) > 80]
                if valid:
                    text_parts.append('\n\n'.join(valid))
            if not text_parts:
                desc_meta = soup.find('meta', attrs={'name': 'description'})
                if desc_meta and desc_meta.get('content') and len(desc_meta['content']) > 100:
                    text_parts.append(desc_meta['content'])
        # Logique Hockey Hebdo (table-based old-school layout)
        if not text_parts and "hockeyhebdo.com" in url:
            for td in soup.find_all('td', attrs={'bgcolor': '#FFFFFF'}):
                txt = td.get_text(strip=True)
                if len(txt) > 500:
                    parts = [c.get_text(' ', strip=True) for c in td.find_all('td') if len(c.get_text(' ', strip=True)) > 50]
                    if parts:
                        text_parts.append('\n\n'.join(parts))
                    break
        # Fallback générique
        if not text_parts:
            body = soup.find('div', itemprop='articleBody') or soup.find('article') or soup.find('main')
            if body:
                text_parts.extend([
                    p.get_text(' ', strip=True) for p in body.find_all('p')
                    if len(p.get_text(strip=True)) > 40
                    and not any(s in p.get_text(strip=True).lower() for s in SKIP_PHRASES)
                ])

        if text_parts:
            # Nettoyage des caractères NULL (PostgreSQL n'aime pas ça)
            clean_parts = [p.replace('\x00', '') for p in text_parts if p]
            return "\n\n".join(dict.fromkeys(clean_parts)), image_caption, True, None, images
        return None, image_caption, True, "No content found", images
    except Exception as e:
        return None, None, True, str(e), []

def run_image_scripts():
    """Lance les scripts TS et retourne un résumé."""
    print("\n[*] Traitement des images et B2...")
    try:
        # Utilisation de tsx (plus robuste sur GitHub Actions/ESM)
        subprocess.run(["node", "-r", "tsx/cjs", "scripts/download_images.ts"], check=True)
        subprocess.run(["node", "-r", "tsx/cjs", "scripts/sync_to_b2.ts"], check=True)
        return "Success"
    except Exception as e:
        return f"Error: {str(e)}"

def main():
    parser = argparse.ArgumentParser(description="Scraper de contenu (mode normal = 24h, --archive = toutes les dates)")
    parser.add_argument("--archive", action="store_true",
                        help="Backfill d'archive : tous les articles lalsace.fr au contenu manquant, sans borne de date")
    parser.add_argument("--limit", type=int, default=0,
                        help="Nombre max d'articles à traiter (défaut : 50 en normal, 300 en archive)")
    parser.add_argument("--max-pages", type=int, default=200,
                        help="Convex archive : pages de scan maximales (défaut 200 x 500 docs)")
    args = parser.parse_args()

    start_time = datetime.now()
    print(f"=== SCRAPER PRODUCTION V2 (WITH LOGS) - {start_time.strftime('%H:%M:%S')} ===")
    if args.archive:
        print("[*] MODE ARCHIVE : toutes les dates (backfill lalsace.fr)")
    
    conn = None
    cur = None
    session_details = []
    stats = {"success": 0, "error": 0, "is_connected": False}

    try:
        conn = None if USE_CONVEX else get_db_connection()
        
        # Récupération des nouveaux champs séparés (Priorité 1)
        db_session = get_app_config(conn, "EBRA_SESSION")
        db_poool = get_app_config(conn, "EBRA_POOOL")
        
        alsace_cookies = None
        cookies_dict = {}

        if db_session:
            # Nettoyage session (gère aussi le format DevTools '.XCONNECT_SESSION :"2=..."')
            s_val = db_session.strip().replace('"', '').replace("'", "")
            if "2=" in s_val:
                s_val = s_val[s_val.find("2="):].split(";")[0].strip()

            # Nettoyage poool : on extrait l'UUID quel que soit le format collé
            p_val = db_poool.strip().replace('"', '').replace("'", "") if db_poool else "9aab6ee3-fda6-43fc-a90e-29de3c73d8f7"
            if "_poool=" in p_val:
                p_val = p_val.split("_poool=")[1].split(";")[0]
            uuid_match = re.search(r'[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}', p_val)
            if uuid_match:
                p_val = uuid_match.group(0)
            
            cookies_dict = {
                ".XCONNECT_SESSION": s_val,
                ".XCONNECTKeepAlive": "2=1",
                ".XCONNECT": "2=1",
                "_poool": p_val
            }
            alsace_cookies = "DB_ACTIVE"
            print(f"[*] Session active via DB (Poool: {p_val[:8]}...)")

        # Fallback sur l'ancien champ EBRA_COOKIE ou Secret GitHub (Priorité 2)
        if not alsace_cookies:
            fallback = get_app_config(conn, "EBRA_COOKIE") or os.environ.get("ALSACE_COOKIES")
            if fallback:
                print("[*] Utilisation du cookie fallback")
                clean = fallback.strip().replace('"', '').replace("'", "")
                if ";" in clean and "=" in clean:
                    for item in clean.split(";"):
                        if "=" in item:
                            k, v = item.split("=", 1)
                            cookies_dict[k.strip()] = v.strip()
                else:
                    session_val = clean[clean.find("2="):].split(";")[0] if "2=" in clean else clean
                    cookies_dict = {".XCONNECT_SESSION": session_val, ".XCONNECTKeepAlive": "2=1", ".XCONNECT": "2=1", "_poool": "9aab6ee3-fda6-43fc-a90e-29de3c73d8f7"}
                alsace_cookies = "FALLBACK_ACTIVE"

        if not USE_CONVEX:
            cur = conn.cursor()

        # Vérification connexion initiale
        try:
            test_resp = requests.get("https://www.lalsace.fr/", cookies=cookies_dict, impersonate="chrome110", timeout=15)
            stats["is_connected"] = any(x in test_resp.text for x in ["Se déconnecter", "Mon compte"])
        except:
            stats["is_connected"] = False
            
        print(f"[*] État initial connexion : {'✅' if stats['is_connected'] else '❌'}")

        if USE_CONVEX:
            if args.archive:
                articles = list_missing_content_via_pages(args.limit or 0)
            else:
                articles = convex_client.get_articles_short_content(limit=args.limit or 50, hours=24)
        else:
            if args.archive:
                # Tous les articles L'Alsace au contenu manquant, du plus ancien
                # au plus récent (les vieux sont traités en premier).
                # Pas de limite par défaut ; `--limit N` borne le run.
                archive_limit = args.limit if args.limit > 0 else None
                cur.execute("""
                    SELECT id, title, link
                    FROM "Article"
                    WHERE link LIKE '%%lalsace.fr%%'
                      AND (content IS NULL OR LENGTH(content) < 150)
                    ORDER BY "publishedAt" ASC NULLS LAST
                    LIMIT %s
                """, (archive_limit,))
            else:
                cur.execute("""
                    SELECT id, title, link
                    FROM "Article"
                    WHERE (content IS NULL OR LENGTH(content) < 500)
                      AND "publishedAt" > NOW() - INTERVAL '24 hours'
                    ORDER BY "publishedAt" DESC LIMIT %s
                """, (args.limit or 50,))
            articles = cur.fetchall()
        
        cooldowns = get_retry_cooldowns(conn)
        total_articles = len(articles)
        total_chars_recovered = 0
        skipped_cooldown = 0
        session_lost = False
        print(f"[*] {total_articles} articles à traiter.")

        for i, article in enumerate(articles, 1):
            if USE_CONVEX:
                art_id = article["link"]
                title = article["title"]
                link = article["link"]
                current_desc = article.get("description")
                current_image_url = article.get("imageUrl")
                current_image_caption = article.get("imageCaption")
                supabase_id = article.get("supabaseId")
            else:
                art_id, title, link = article
                # On récupère la description actuelle pour le fallback
                cur.execute('SELECT description, "imageUrl", "imageCaption" FROM "Article" WHERE id = %s', (art_id,))
                row_desc = cur.fetchone()
                current_desc = row_desc[0] if row_desc else None
                current_image_url = row_desc[1] if row_desc else None
                current_image_caption = row_desc[2] if row_desc else None
                supabase_id = None

            # Article déjà en échec : sauter tant que le cooldown n'est pas expiré
            # (évite de retenter en boucle les pages injoignables / trop courtes)
            if cooldown_active(cooldowns, art_id):
                until, fails = _parse_cooldown_entry(cooldowns.get(art_id))
                skipped_cooldown += 1
                print(f"    [⏳] En cooldown jusqu'à {until:%H:%M} (essai {fails}), ignoré : {title[:40]}...")
                continue

            # Session EBRA perdue plus tôt dans ce run : ne pas refetch le paywall
            is_ebra = any(d in link for d in ("lalsace.fr", "dna.fr", "estrepublicain.fr", "vosgesmatin.fr"))
            if session_lost and is_ebra:
                until, fails, hours = mark_retry_cooldown(
                    cooldowns, art_id, "session_lost", increment=False
                )
                skipped_cooldown += 1
                print(f"    [⏳] Session perdue, cooldown {hours}h : {title[:40]}...")
                continue

            # Tentative d'extraction du contenu complet
            content, image_caption, active, err, images = fetch_article_content(link, cookies_dict, alsace_cookies is not None)

            # Enregistrement de toutes les images (hero + galerie) dans ArticleImage
            images_changed = False
            if images:
                # Convex : articleId doit être l'UUID Supabase (supabaseId),
                # clé de jointure de articleImages côté Convex.
                image_article_id = supabase_id if USE_CONVEX else art_id
                if image_article_id:
                    images_changed = sync_article_images(conn, image_article_id, images, current_image_url, current_image_caption)
            
            status = "SUCCESS" if content else "FAILED"
            
            # Si l'extraction échoue, on utilise la description comme contenu de secours
            final_content = content
            if not final_content and current_desc:
                final_content = current_desc
                status = "FALLBACK"
                print(f"    [💡] Utilisation de la description pour : {title[:40]}...")
            
            if not active:
                status = "SESSION_LOST"
                session_lost = True
            
            updated = images_changed
            if image_caption:
                if USE_CONVEX:
                    convex_client.upsert_article({"link": art_id, "imageCaption": image_caption})
                else:
                    cur.execute(
                        'UPDATE "Article" SET "imageCaption" = %s WHERE id = %s',
                        (image_caption, art_id),
                    )
                updated = True

            current_len = len(final_content) if final_content else 0
            if final_content and current_len >= SAVE_CONTENT_MIN:
                if USE_CONVEX:
                    convex_client.upsert_article({
                        "link": art_id,
                        "content": final_content,
                        "updatedAt": int(time.time() * 1000),
                    })
                else:
                    cur.execute('UPDATE "Article" SET content = %s, "updatedAt" = NOW() WHERE id = %s', (final_content, art_id))
                updated = True
                if status == "SUCCESS" and current_len >= FULL_CONTENT_MIN:
                    stats["success"] += 1
            else:
                if final_content:
                    print(f"    [⚠️] Contenu trop court ({current_len} chars), ignoré : {title[:40]}...")
                stats["error"] += 1

            # Backoff : ne pas refetch à chaque cron 15 min.
            #  - plein texte (>= 500) : succès, on oublie le cooldown
            #  - article court mais réel : 7 j (le HTML ne grandira pas)
            #  - 404/410 : 7 j
            #  - fallback / échec réseau / paywall : backoff exponentiel
            err_l = (err or "").lower()
            if status == "SUCCESS" and current_len >= FULL_CONTENT_MIN:
                cooldowns.pop(art_id, None)
            else:
                if "404" in err_l or (err or "").startswith("HTTP 404"):
                    reason = "http_404"
                elif "410" in err_l:
                    reason = "http_410"
                elif status == "SESSION_LOST":
                    reason = "session_lost"
                elif status == "FALLBACK":
                    reason = "fallback"
                elif status == "SUCCESS" and current_len < FULL_CONTENT_MIN:
                    reason = "short"
                else:
                    reason = "failed"
                until, fails, hours = mark_retry_cooldown(cooldowns, art_id, reason)
                print(f"    [⏳] Cooldown {hours}h (essai {fails}, {reason}) : {title[:40]}...")

            if updated and not USE_CONVEX:
                conn.commit()
            
            session_details.append({"title": title, "link": link, "status": status, "error": err, "chars": current_len})
            if status == "SUCCESS" and current_len:
                total_chars_recovered += current_len
            elapsed = (datetime.now() - start_time).total_seconds()
            pct = 100.0 * i / total_articles if total_articles else 100.0
            eta = (elapsed / i) * (total_articles - i) if i else 0
            print(f"    [{i}/{total_articles}] ({pct:5.1f}% | {int(elapsed // 60):02d}m{int(elapsed % 60):02d}s | ETA {int(eta // 60):02d}m{int(eta % 60):02d}s) {status} | {title[:40]}...", flush=True)

        if total_chars_recovered:
            print(f"\n[*] Taille totale récupérée : {total_chars_recovered:,} chars ({total_chars_recovered/1_048_576:.2f} Mo)", flush=True)
        print(
            f"[*] Cooldown : {skipped_cooldown} ignorés (pas de refetch HTTP) / "
            f"{total_articles} candidats",
            flush=True,
        )

        prune_retry_cooldowns(cooldowns)
        persist_retry_cooldowns(conn, cooldowns)

        # Rattrapage légendes photo (articles récents sans imageCaption)
        if USE_CONVEX:
            caption_rows = convex_client.get_articles_missing_captions(limit=30)
        else:
            cur.execute("""
                SELECT id, link FROM "Article"
                WHERE "imageCaption" IS NULL
                  AND "imageUrl" IS NOT NULL AND "imageUrl" <> ''
                  AND "publishedAt" > NOW() - INTERVAL '14 days'
                  AND (
                    link LIKE '%lalsace.fr%' OR link LIKE '%dna.fr%'
                    OR link LIKE '%estrepublicain.fr%' OR link LIKE '%vosgesmatin.fr%'
                  )
                ORDER BY "publishedAt" DESC LIMIT 30
            """)
            caption_rows = cur.fetchall()
        if caption_rows:
            print(f"\n[*] Rattrapage légendes photo : {len(caption_rows)} articles...")
            caption_ok = 0
            for row in caption_rows:
                if USE_CONVEX:
                    art_id, link = row["link"], row["link"]
                else:
                    art_id, link = row
                caption_result = fetch_page_caption(link, cookies_dict, alsace_cookies is not None)
                if caption_result.caption:
                    if USE_CONVEX:
                        convex_client.upsert_article({"link": art_id, "imageCaption": caption_result.caption})
                    else:
                        cur.execute(
                            'UPDATE "Article" SET "imageCaption" = %s WHERE id = %s',
                            (caption_result.caption, art_id),
                        )
                    if not USE_CONVEX:
                        conn.commit()
                    caption_ok += 1
            print(f"    Légendes récupérées : {caption_ok}/{len(caption_rows)}")

        # Image processing
        img_status = run_image_scripts()

        # Enregistrement du LOG final
        finished_at = datetime.now()
        status_final = "SUCCESS" if stats["error"] == 0 else "PARTIAL"
        if any(d["status"] == "SESSION_LOST" for d in session_details): status_final = "SESSION_LOST"

        try:
            if USE_CONVEX:
                convex_client.insert_scraping_log(
                    started_at=start_time,
                    finished_at=finished_at,
                    status=status_final,
                    is_connected=stats["is_connected"],
                    articles_count=len(articles),
                    success_count=stats["success"],
                    error_count=stats["error"],
                    details=json.dumps(session_details),
                )
            else:
                cur.execute("""
                    INSERT INTO "ScrapingLog" (id, "startedAt", "finishedAt", status, "isConnected", "articlesCount", "successCount", "errorCount", details)
                    VALUES (gen_random_uuid(), %s, %s, %s, %s, %s, %s, %s, %s)
                """, (start_time, finished_at, status_final, stats["is_connected"], len(articles), stats["success"], stats["error"], json.dumps(session_details)))
                conn.commit()
            print(f"\n✅ Log enregistré en base de données. Statut: {status_final}")
        except Exception as log_err:
            if not USE_CONVEX:
                conn.rollback()
            print(f"\n[!] Log non enregistré (table absente?) : {log_err}")

    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"❌ Erreur critique : {e}")
        if USE_CONVEX:
            try:
                convex_client.insert_scraping_log(
                    started_at=start_time,
                    status="FAILED",
                    error_message=str(e),
                )
            except Exception:
                pass
        elif conn:
            try:
                conn.rollback()
                cur = conn.cursor()
                cur.execute("""
                    INSERT INTO "ScrapingLog" (id, "startedAt", "finishedAt", status, "errorMessage")
                    VALUES (gen_random_uuid(), %s, NOW(), 'FAILED', %s)
                """, (start_time, str(e)))
                conn.commit()
            except: pass
    finally:
        if conn: conn.close()

if __name__ == "__main__":
    main()
