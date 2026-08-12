import os
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
        time.sleep(random.uniform(0.5, 1.2))
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

DATABASE_URL = os.environ.get("DATABASE_URL")

def get_db_connection():
    if not DATABASE_URL:
        raise ValueError("DATABASE_URL is not set")
    clean_url = DATABASE_URL.replace("?pgbouncer=true", "").replace("&pgbouncer=true", "")
    return psycopg2.connect(clean_url)

def get_app_config(conn, key):
    try:
        with conn.cursor() as cur:
            cur.execute('SELECT value FROM "AppConfig" WHERE key = %s', (key,))
            row = cur.fetchone()
            return row[0] if row else None
    except:
        return None

RETRY_COOLDOWN_KEY = "SCRAPE_CONTENT_RETRY_COOLDOWNS"
RETRY_COOLDOWN_HOURS = 6


def get_retry_cooldowns(conn):
    """Cooldowns d'échec par article : {article_id: "YYYY-MM-DDTHH:MM:SS"}."""
    raw = get_app_config(conn, RETRY_COOLDOWN_KEY)
    if not raw:
        return {}
    try:
        data = json.loads(raw)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def persist_retry_cooldowns(conn, cooldowns):
    if not cooldowns:
        return
    try:
        with conn.cursor() as cur:
            cur.execute(
                'INSERT INTO "AppConfig" (key, value, "updatedAt") VALUES (%s, %s, NOW()) '
                'ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value, "updatedAt" = NOW()',
                (RETRY_COOLDOWN_KEY, json.dumps(cooldowns)),
            )
        conn.commit()
    except Exception as e:
        print(f"[!] Cooldowns de retry non persistés : {e}")

def sync_article_images(conn, article_id, images, image_url, image_caption):
    """Enregistre toutes les images d'un article dans ArticleImage.

    L'image hero (imageUrl BDD) est toujours position 0. Les autres images
    sont ajoutées/actualisées par URL, sans doublon.
    """
    if not images and not image_url:
        return False

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

        time.sleep(random.uniform(1.0, 2.0))
        
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
    start_time = datetime.now()
    print(f"=== SCRAPER PRODUCTION V2 (WITH LOGS) - {start_time.strftime('%H:%M:%S')} ===")
    
    conn = None
    session_details = []
    stats = {"success": 0, "error": 0, "is_connected": False}

    try:
        conn = get_db_connection()
        
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

        cur = conn.cursor()

        # Vérification connexion initiale
        try:
            test_resp = requests.get("https://www.lalsace.fr/", cookies=cookies_dict, impersonate="chrome110", timeout=15)
            stats["is_connected"] = any(x in test_resp.text for x in ["Se déconnecter", "Mon compte"])
        except:
            stats["is_connected"] = False
            
        print(f"[*] État initial connexion : {'✅' if stats['is_connected'] else '❌'}")

        cur.execute("""
            SELECT id, title, link 
            FROM "Article" 
            WHERE (content IS NULL OR LENGTH(content) < 500)
              AND "publishedAt" > NOW() - INTERVAL '24 hours'
            ORDER BY "publishedAt" DESC LIMIT 50
        """)
        articles = cur.fetchall()
        
        cooldowns = get_retry_cooldowns(conn)
        
        for i, (art_id, title, link) in enumerate(articles, 1):
            # Article déjà en échec : sauter tant que le cooldown n'est pas expiré
            # (évite de retenter en boucle les pages injoignables à chaque run)
            cooldown_until = cooldowns.get(art_id)
            if cooldown_until:
                try:
                    until = datetime.fromisoformat(cooldown_until)
                    if datetime.now() < until:
                        print(f"    [⏳] En cooldown jusqu'à {until:%H:%M}, ignoré : {title[:40]}...")
                        continue
                except ValueError:
                    pass
                del cooldowns[art_id]
            # On récupère la description actuelle pour le fallback
            cur.execute('SELECT description, "imageUrl", "imageCaption" FROM "Article" WHERE id = %s', (art_id,))
            row_desc = cur.fetchone()
            current_desc = row_desc[0] if row_desc else None
            current_image_url = row_desc[1] if row_desc else None
            current_image_caption = row_desc[2] if row_desc else None

            # Tentative d'extraction du contenu complet
            content, image_caption, active, err, images = fetch_article_content(link, cookies_dict, alsace_cookies is not None)

            # Enregistrement de toutes les images (hero + galerie) dans ArticleImage
            images_changed = False
            if images:
                images_changed = sync_article_images(conn, art_id, images, current_image_url, current_image_caption)
            
            status = "SUCCESS" if content else "FAILED"
            
            # Si l'extraction échoue, on utilise la description comme contenu de secours
            final_content = content
            if not final_content and current_desc:
                final_content = current_desc
                status = "FALLBACK"
                print(f"    [💡] Utilisation de la description pour : {title[:40]}...")
            
            # On ne break plus si la session est perdue, on continue pour les autres
            if not active:
                status = "SESSION_LOST"
            
            updated = images_changed
            if image_caption:
                cur.execute(
                    'UPDATE "Article" SET "imageCaption" = %s WHERE id = %s',
                    (image_caption, art_id),
                )
                updated = True

            if final_content and len(final_content) >= 150:
                cur.execute('UPDATE "Article" SET content = %s, "updatedAt" = NOW() WHERE id = %s', (final_content, art_id))
                updated = True
                if status != "FALLBACK": stats["success"] += 1
            else:
                # Contenu trop court ou absent : ne pas sauvegarder pour éviter la boucle
                # (article restera NULL et sera retesté au prochain run)
                if final_content:
                    print(f"    [⚠️] Contenu trop court ({len(final_content)} chars), ignoré : {title[:40]}...")
                stats["error"] += 1

            # Marquer les échecs d'un cooldown pour ne plus retenter en boucle
            # (page injoignable, paywall bloqué, contenu introuvable...)
            current_len = len(final_content) if final_content else 0
            if status in ("FAILED", "SESSION_LOST") or current_len < 150:
                cooldowns[art_id] = (datetime.now() + timedelta(hours=RETRY_COOLDOWN_HOURS)).isoformat()
            else:
                cooldowns.pop(art_id, None)

            if updated:
                conn.commit()
            
            session_details.append({"title": title, "link": link, "status": status, "error": err, "chars": current_len})
            print(f"    [{i}/{len(articles)}] {status} | {title[:40]}...")

        persist_retry_cooldowns(conn, cooldowns)

        # Rattrapage légendes photo (articles récents sans imageCaption)
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
            for art_id, link in caption_rows:
                caption_result = fetch_page_caption(link, cookies_dict, alsace_cookies is not None)
                if caption_result.caption:
                    cur.execute(
                        'UPDATE "Article" SET "imageCaption" = %s WHERE id = %s',
                        (caption_result.caption, art_id),
                    )
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
            cur.execute("""
                INSERT INTO "ScrapingLog" (id, "startedAt", "finishedAt", status, "isConnected", "articlesCount", "successCount", "errorCount", details)
                VALUES (gen_random_uuid(), %s, %s, %s, %s, %s, %s, %s, %s)
            """, (start_time, finished_at, status_final, stats["is_connected"], len(articles), stats["success"], stats["error"], json.dumps(session_details)))
            conn.commit()
            print(f"\n✅ Log enregistré en base de données. Statut: {status_final}")
        except Exception as log_err:
            conn.rollback()
            print(f"\n[!] Log non enregistré (table absente?) : {log_err}")

    except Exception as e:
        print(f"❌ Erreur critique : {e}")
        if conn:
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
