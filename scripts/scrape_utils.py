"""Utilitaires partagés entre les scripts de scraping."""
import html as htmllib
import json
import re
import time
import random
import unicodedata
from dataclasses import dataclass
from urllib.parse import urlparse
from bs4 import BeautifulSoup
from curl_cffi import requests


@dataclass
class CaptionFetchResult:
    caption: str | None = None
    fetched: bool = False
    status_code: int | None = None

EBRA_DOMAINS = ("lalsace.fr", "dna.fr", "estrepublicain.fr", "vosgesmatin.fr")


def fetch_sitemap_xml(url: str, retries: int = 3, timeout: int = 60) -> str:
    """Télécharge un sitemap XML avec retries sur erreurs 5xx / réseau.

    Les 502/503 transitoires (WAF, Cloudflare, surcharge) ne doivent pas faire
    échouer un run : on réessaie avec backoff avant d'abandonner.
    """
    last_error = None
    for attempt in range(1, retries + 1):
        try:
            resp = requests.get(url, timeout=timeout, impersonate="chrome110")
            if resp.status_code < 500 and resp.status_code != 429:
                return resp.text
            last_error = f"HTTP {resp.status_code}"
        except Exception as exc:
            last_error = str(exc) or exc.__class__.__name__
        if attempt < retries:
            delay = 3 * attempt
            print(
                f"   ⚠️ Sitemap {url} : {last_error} — "
                f"nouvelle tentative dans {delay}s ({attempt}/{retries})"
            )
            time.sleep(delay)
    raise RuntimeError(f"Sitemap {url} : {last_error} après {retries} tentatives")


def is_ebra_url(url: str) -> bool:
    return any(d in url for d in EBRA_DOMAINS)


def is_jds_url(url: str) -> bool:
    return "jds.fr" in url


# Rubrique d'édition Mulhouse-Thann dans le chemin (pas seulement le slug).
_MULHOUSE_PATH_RE = re.compile(
    r"/(?:edition-mulhouse(?:-thann)?|secteur-de-mulhouse)(?:/|$)",
    re.I,
)

def is_mulhouse_url(url: str) -> bool:
    """L'URL parle-t-elle de Mulhouse, sans ouvrir la page ?

    Le slug seul ratait « Une maison de l'urbanisme au Grand Rex »
    (`/haut-rhin/2013/11/09/une-maison-de-l-urbanisme-au-grand-rex`) : Mulhouse
    est dans le fil d'Ariane, pas dans le dernier segment. On inspecte aussi
    les dossiers du chemin (`/edition-mulhouse-thann/`, `/mulhouse/`).
    « centre-ville » n'est PAS un critère d'URL : trop d'éditions L'Alsace
    ont un centre-ville. Le kicker se juge sur le HTML (html_is_mulhouse_edition).
    """
    try:
        path = urlparse(url).path.lower()
    except Exception:
        path = (url or "").lower()
    if _MULHOUSE_PATH_RE.search(path):
        return True
    parts = [p for p in path.split("/") if p]
    slug = parts[-1] if parts else ""
    for folder in parts[:-1]:
        if folder in ("mulhouse",) or folder.startswith("mulhous"):
            return True
        if "mulhouse" in folder.split("-") and folder != "rmulhouse":
            return True
    tokens = slug.split("-")
    if tokens == ["mulhouse"]:
        return False
    if tokens[0] == "mulhouse" and len(tokens) > 1 and tokens[1].isdigit():
        return False
    if tokens[0] == "r" and len(tokens) > 1 and tokens[1] == "mulhouse":
        return False
    for token in tokens:
        if token == "mulhouse":
            return True
        if token.startswith("mulhous"):
            return True
        if token != "rmulhouse" and token.endswith("mulhouse"):
            return True
    return False


def html_is_mulhouse_edition(html: str) -> bool:
    """L'article EST classé Mulhouse, pas seulement la page L'Alsace.

    Interdit : le widget « Articles les plus lus Édition Mulhouse - Thann »
    présent sur TOUTES les pages (Indochine, Mika… ingérés par erreur).

    On ne garde que :
    - le cran de fil d'Ariane commune `/edition-mulhouse-thann/mulhouse`
    - le tag geo INSEE 68224-mulhouse
    """
    if not html:
        return False
    low = html.lower()
    if "/edition-mulhouse-thann/mulhouse" in low:
        return True
    if "68224-mulhouse" in low:
        return True
    return False


def ebra_target_url(url: str, alsace_cookies_active: bool) -> str:
    if alsace_cookies_active and any(d in url for d in ("dna.fr", "estrepublicain.fr", "vosgesmatin.fr")):
        return (
            url.replace("www.dna.fr", "www.lalsace.fr")
            .replace("www.estrepublicain.fr", "www.lalsace.fr")
            .replace("www.vosgesmatin.fr", "www.lalsace.fr")
        )
    return url


def _clean_caption(text: str | None) -> str | None:
    if not text:
        return None
    caption = htmllib.unescape(text).strip()
    caption = re.sub(r"\s+", " ", caption)
    if len(caption) < 5:
        return None
    lower = caption.lower()
    if lower in ("l'alsace", "dna", "est républicain", "screenshot") or _is_junk_caption(caption):
        return None
    return caption


def _extract_video_caption(soup: BeautifulSoup) -> str | None:
    """Pages /videos/ EBRA : pas de figcaption, mais description dans le JSON-LD."""
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            raw = script.string
            if not raw:
                continue
            data = json.loads(raw.strip())
            items = data if isinstance(data, list) else [data]
            for item in items:
                if not isinstance(item, dict):
                    continue
                if item.get("@type") != "VideoObject":
                    continue
                desc = item.get("description") or item.get("name")
                if desc and len(str(desc)) > 20:
                    return _clean_caption(str(desc))
        except (json.JSONDecodeError, TypeError):
            continue

    og_desc = soup.find("meta", property="og:description")
    if og_desc and og_desc.get("content") and len(og_desc["content"]) > 20:
        return _clean_caption(og_desc["content"])

    return None


def _is_duration_caption(text: str) -> bool:
    """Ignore les durées vidéo (ex. BFM « 2:10 ») prises pour des légendes."""
    return bool(re.match(r"^\d{1,2}:\d{2}(:\d{2})?$", text.strip()))


def _is_junk_caption(text: str) -> bool:
    lower = text.lower().strip()
    if lower in (
        "screenshot",
        "information légende",
        "information legende",
        "légende",
        "legende",
        "image de la une",
    ):
        return True
    return lower.startswith("information ") and "légende" in lower


def _first_caption_from_container(container) -> str | None:
    for figcap in container.find_all("figcaption"):
        text = figcap.get_text(" ", strip=True)
        if (
            text
            and len(text) > 5
            and "l'alsace" not in text.lower()
            and not _is_duration_caption(text)
            and not _is_junk_caption(text)
        ):
            return text
    for el in container.select(".wp-caption-text, .photo-credit, .image-credit, .legend, .legende"):
        text = el.get_text(" ", strip=True)
        if text and len(text) > 5 and not _is_junk_caption(text):
            return text
    return None


def _normalize_image_path(url: str) -> str:
    if not url:
        return ""
    path = url.split("?")[0].lower()
    name = path.rstrip("/").split("/")[-1]
    name = re.sub(r"(-\d{3,}){1,3}\.(webp|jpg|jpeg|png|gif)$", "", name)
    name = re.sub(r"\.(webp|jpg|jpeg|png|gif)$", "", name)
    return name


def _image_urls_match(page_src: str, image_url: str) -> bool:
    if not page_src or not image_url:
        return False
    a = _normalize_image_path(page_src)
    b = _normalize_image_path(image_url)
    if not a or not b:
        return False
    if a == b or a in b or b in a:
        return True
    min_len = min(len(a), len(b), 24)
    return min_len >= 12 and a[:min_len] == b[:min_len]


def _hero_alt_from_image_url(soup: BeautifulSoup, image_url: str) -> str | None:
    """Alt de l'image hero identifiée via imageUrl BDD (JDS, Alterpresse68…)."""
    for img in soup.find_all("img"):
        src = img.get("src") or img.get("data-src") or img.get("data-lazy-src") or ""
        if not _image_urls_match(src, image_url):
            continue
        alt = (img.get("alt") or "").strip()
        caption = _clean_caption(alt)
        if caption:
            return caption
    return None


def extract_image_caption(
    soup: BeautifulSoup, url: str, image_url: str | None = None
) -> str | None:
    """Extrait la légende de la photo principale (ou description vidéo)."""
    if "/video" in url.lower():
        video_caption = _extract_video_caption(soup)
        if video_caption:
            return video_caption

    if "le-periscope.info" in url:
        periscope_caption = _extract_periscope_hero_caption(soup, url, image_url)
        if periscope_caption:
            return periscope_caption

    caption = None

    if is_ebra_url(url):
        figure = soup.find("figure", class_="mainImage")
        if figure:
            figcap = figure.find("figcaption", class_="caption") or figure.find("figcaption")
            if figcap:
                caption = figcap.get_text(" ", strip=True)
            if not caption:
                img = figure.find("img")
                if img and img.get("alt"):
                    caption = img["alt"].strip()

    if not caption and image_url:
        caption = _hero_alt_from_image_url(soup, image_url)

    if not caption:
        for container in (soup.find("article"), soup.find("main"), soup):
            if not container:
                continue
            caption = _first_caption_from_container(container)
            if caption:
                break

    if not caption:
        img = soup.find("meta", property="og:image:alt")
        if img and img.get("content"):
            caption = img["content"].strip()

    return _clean_caption(caption)


def fetch_page_caption(
    url: str,
    cookies_dict: dict,
    alsace_cookies_active: bool,
    image_url: str | None = None,
) -> CaptionFetchResult:
    """Télécharge la page et extrait la légende image.

    fetched=True : page accessible (HTTP 200), caption None = source sans légende.
    fetched=False : erreur réseau, timeout ou HTTP non-200.
    """
    try:
        target_url = ebra_target_url(url, alsace_cookies_active)
        time.sleep(random.uniform(0.3, 0.8))
        try:
            resp = requests.get(
                target_url,
                cookies=cookies_dict,
                impersonate="chrome120",
                timeout=20,
                allow_redirects=True,
            )
        except Exception as ssl_err:
            if "CertificateVerifyError" in str(ssl_err) or "SSL" in str(ssl_err):
                resp = requests.get(
                    target_url,
                    cookies=cookies_dict,
                    impersonate="chrome120",
                    timeout=20,
                    allow_redirects=True,
                    verify=False,
                )
            else:
                raise ssl_err
        if resp.status_code != 200:
            return CaptionFetchResult(fetched=False, status_code=resp.status_code)
        soup = BeautifulSoup(resp.text, "html.parser")
        return CaptionFetchResult(
            caption=extract_image_caption(soup, target_url, image_url),
            fetched=True,
            status_code=resp.status_code,
        )
    except Exception:
        return CaptionFetchResult(fetched=False)


def _iter_mplusinfo_content_html(obj, depth=0):
    if depth > 15:
        return
    if isinstance(obj, dict):
        if obj.get("content_html"):
            yield str(obj["content_html"])
            return
        for value in obj.values():
            yield from _iter_mplusinfo_content_html(value, depth + 1)
    elif isinstance(obj, list):
        for item in obj:
            yield from _iter_mplusinfo_content_html(item, depth + 1)


def _extract_mplusinfo_content_html(soup: BeautifulSoup) -> str | None:
    next_data = soup.find("script", id="__NEXT_DATA__")
    if next_data and next_data.string:
        try:
            data = json.loads(next_data.string)
            chunks = list(_iter_mplusinfo_content_html(data))
            if chunks:
                return _mplusinfo_html_to_text(chunks)
        except (json.JSONDecodeError, TypeError):
            pass

    for script in soup.find_all("script"):
        if not script.string or "content_html" not in script.string:
            continue
        txt = script.string.strip()
        if txt.startswith('{"status"'):
            try:
                outer = json.loads(txt)
                inner = json.loads(outer["body"])
                chunks = list(_iter_mplusinfo_content_html(inner))
                if chunks:
                    return _mplusinfo_html_to_text(chunks)
            except (json.JSONDecodeError, TypeError, KeyError):
                pass

    article = soup.find("article") or soup.find("main")
    if article:
        paragraphs = [
            p.get_text(" ", strip=True)
            for p in article.find_all("p")
            if len(p.get_text(strip=True)) > 40
        ]
        if paragraphs:
            return "\n\n".join(dict.fromkeys(paragraphs))

    return None


def _mplusinfo_html_to_text(chunks: list[str]) -> str:
    texts = []
    for chunk in chunks:
        text = BeautifulSoup(chunk, "html.parser").get_text("\n", strip=True)
        if text:
            texts.append(text)
    return "\n\n".join(dict.fromkeys(texts))


def _parse_mplusinfo_image(image_field) -> str | None:
    if isinstance(image_field, str):
        return image_field
    if isinstance(image_field, dict):
        return image_field.get("url") or image_field.get("@id")
    if isinstance(image_field, list) and image_field:
        return _parse_mplusinfo_image(image_field[0])
    return None


def _parse_mplusinfo_image_caption(image_field) -> str | None:
    if isinstance(image_field, dict):
        return _clean_caption(image_field.get("caption"))
    return None


def _clean_mplusinfo_title(title: str | None) -> str | None:
    if not title:
        return None
    title = htmllib.unescape(title).strip()
    title = re.sub(r"\s*[-|]\s*mplusinfo\.fr\s*$", "", title, flags=re.I)
    title = re.sub(r"\s*\|\s*M\+\s*$", "", title)
    return title.strip() or None


def parse_mplusinfo_article(soup: BeautifulSoup, url: str) -> dict:
    """Extrait métadonnées et contenu d'une page mplusinfo.fr."""
    title = None
    description = None
    image_url = None
    image_caption = None
    published_at = None
    content = None

    og_title = soup.find("meta", property="og:title")
    if og_title and og_title.get("content"):
        title = _clean_mplusinfo_title(og_title["content"])

    og_desc = soup.find("meta", property="og:description")
    if og_desc and og_desc.get("content"):
        description = htmllib.unescape(og_desc["content"]).strip()

    og_image = soup.find("meta", property="og:image")
    if og_image and og_image.get("content"):
        image_url = htmllib.unescape(og_image["content"]).strip()

    pub_meta = soup.find("meta", property="article:published_time")
    if pub_meta and pub_meta.get("content"):
        published_at = _parse_iso_datetime(pub_meta["content"])

    for script in soup.find_all("script", type="application/ld+json"):
        try:
            raw = script.string
            if not raw:
                continue
            data = json.loads(raw.strip())
            items = data if isinstance(data, list) else [data]
            for item in items:
                if not isinstance(item, dict) or item.get("@type") != "NewsArticle":
                    continue
                if not title and item.get("headline"):
                    title = _clean_mplusinfo_title(str(item["headline"]))
                if not description and item.get("description"):
                    description = htmllib.unescape(str(item["description"])).strip()
                if not published_at and item.get("datePublished"):
                    published_at = _parse_iso_datetime(str(item["datePublished"]))
                if not image_url:
                    image_url = _parse_mplusinfo_image(item.get("image"))
                if not image_caption:
                    image_caption = _parse_mplusinfo_image_caption(item.get("image"))
                break
        except (json.JSONDecodeError, TypeError):
            continue

    if not title:
        h1 = soup.find("h1")
        if h1:
            title = _clean_mplusinfo_title(h1.get_text(strip=True))

    if not image_caption:
        image_caption = extract_image_caption(soup, url, image_url)

    content = _extract_mplusinfo_content_html(soup)
    if content:
        content = content.replace("\x00", "")

    if not description and content:
        description = content[:300]

    return {
        "title": title,
        "description": description or "",
        "image_url": image_url,
        "image_caption": image_caption,
        "published_at": published_at,
        "content": content,
    }


def _parse_iso_datetime(value: str | None):
    from datetime import datetime, timezone

    if not value:
        return None
    value = value.strip().replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(value)
        if dt.tzinfo is not None:
            dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
        return dt
    except ValueError:
        return None


def fetch_mplusinfo_page(url: str) -> BeautifulSoup | None:
    try:
        time.sleep(random.uniform(0.4, 1.0))
        resp = requests.get(url, impersonate="chrome110", timeout=25, allow_redirects=True)
        if resp.status_code != 200:
            return None
        return BeautifulSoup(resp.text, "html.parser")
    except Exception:
        return None


def normalize_text(text: str | None) -> str:
    if not text:
        return ""
    text = text.lower()
    return "".join(c for c in unicodedata.normalize("NFKD", text) if not unicodedata.combining(c))


def is_mulhouse_related(title: str, description: str | None = None, content: str | None = None) -> bool:
    haystack = normalize_text(f"{title} {description or ''} {content or ''}")
    return "mulhous" in haystack


def fetch_periscope_page(url: str) -> BeautifulSoup | None:
    try:
        time.sleep(random.uniform(0.4, 1.0))
        resp = requests.get(url, impersonate="chrome110", timeout=25, allow_redirects=True)
        if resp.status_code != 200:
            return None
        return BeautifulSoup(resp.text, "html.parser")
    except Exception:
        return None


def _clean_periscope_title(title: str | None) -> str | None:
    if not title:
        return None
    title = htmllib.unescape(title).strip()
    title = re.sub(r"\s*[-|]\s*le periscope\s*$", "", title, flags=re.I)
    title = re.sub(r"\s*[-|]\s*le périscope\s*$", "", title, flags=re.I)
    return title.strip() or None


PERISCOPE_BLOCK_TAGS = frozenset({"p", "h2", "h3", "h4", "figure", "ul", "ol", "blockquote"})


def _find_periscope_content_root(soup: BeautifulSoup):
    for cls in ("ph-single-content__body", "entry-content"):
        node = soup.find("div", class_=cls)
        if node:
            return node
    return soup.find("article") or soup.find("main")


def _absolute_periscope_url(page_url: str, src: str | None) -> str | None:
    if not src:
        return None
    src = src.strip()
    if not src or src.startswith("data:"):
        return None
    if src.startswith("//"):
        return f"https:{src}"
    if src.startswith("/"):
        from urllib.parse import urljoin

        return urljoin(page_url, src)
    if src.startswith("http"):
        return src
    return None


def _is_periscope_junk_block(element) -> bool:
    if not element or not getattr(element, "name", None):
        return True
    if "addtoany" in str(element).lower():
        return True
    classes = " ".join(element.get("class") or []).lower()
    if any(x in classes for x in ("sharedaddy", "addtoany", "wp-block-embed")):
        return True
    return False


def _is_periscope_junk_text(text: str) -> bool:
    if not text or len(text) < 5:
        return True
    lower = text.lower().strip()
    if lower.startswith(("édition :", "partager", "partagez")):
        return True
    return _is_junk_caption(text)


def _periscope_image_caption(block, img) -> str | None:
    figure = img.find_parent("figure")
    if figure:
        figcap = figure.find("figcaption")
        if figcap:
            caption = _clean_caption(figcap.get_text(" ", strip=True))
            if caption:
                return caption

    search_blocks = [block, img.parent]
    for parent in img.parents:
        if parent is block:
            continue
        classes = " ".join(parent.get("class") or []).lower()
        if "wp-caption" in classes or "wp-block-image" in classes:
            search_blocks.append(parent)
            break

    for container in search_blocks:
        if not container:
            continue
        for selector in (".wp-caption-text", ".photo-credit", ".image-credit", ".legend", ".legende"):
            cap_el = container.select_one(selector)
            if cap_el:
                caption = _clean_caption(cap_el.get_text(" ", strip=True))
                if caption:
                    return caption

    alt = _clean_caption((img.get("alt") or "").strip())
    if alt:
        return alt
    return None


def _append_periscope_image_html(parts: list[str], img, page_url: str, block=None) -> None:
    src = _absolute_periscope_url(
        page_url,
        img.get("src") or img.get("data-src") or img.get("data-lazy-src"),
    )
    if not src:
        return
    caption = _periscope_image_caption(block or img.parent, img)
    alt = htmllib.escape(caption or "", quote=True)
    src_esc = htmllib.escape(src, quote=True)
    parts.append(f'<p><img src="{src_esc}" alt="{alt}"></p>')
    if caption:
        parts.append(f"<p><em>{htmllib.escape(caption)}</em></p>")


def _append_periscope_text_html(parts: list[str], tag: str, text: str) -> None:
    if _is_periscope_junk_text(text):
        return
    parts.append(f"<{tag}>{htmllib.escape(text)}</{tag}>")


def _extract_periscope_hero_caption(
    soup: BeautifulSoup, page_url: str, image_url: str | None
) -> str | None:
    root = _find_periscope_content_root(soup)
    if not root:
        return None

    for img in root.find_all("img"):
        src = _absolute_periscope_url(
            page_url,
            img.get("src") or img.get("data-src") or img.get("data-lazy-src"),
        )
        if not src:
            continue
        if image_url and not _image_urls_match(src, image_url):
            continue
        caption = _periscope_image_caption(img.parent, img)
        if caption:
            return caption
    return None


def _extract_periscope_content(soup: BeautifulSoup, page_url: str = "") -> str | None:
    container = _find_periscope_content_root(soup)
    if not container:
        return None

    parts: list[str] = []
    seen_text: set[str] = set()
    seen_images: set[str] = set()

    for element in container.find_all(PERISCOPE_BLOCK_TAGS):
        if _is_periscope_junk_block(element):
            continue
        if any(
            parent.name in PERISCOPE_BLOCK_TAGS and parent is not container
            for parent in element.parents
        ):
            continue

        if element.name == "figure":
            img = element.find("img")
            if img:
                src = _absolute_periscope_url(
                    page_url,
                    img.get("src") or img.get("data-src") or img.get("data-lazy-src"),
                )
                if src and src not in seen_images:
                    seen_images.add(src)
                    _append_periscope_image_html(parts, img, page_url, element)
            continue

        imgs = element.find_all("img")
        text = element.get_text(" ", strip=True)

        if imgs:
            for img in imgs:
                src = _absolute_periscope_url(
                    page_url,
                    img.get("src") or img.get("data-src") or img.get("data-lazy-src"),
                )
                if not src or src in seen_images:
                    continue
                seen_images.add(src)
                _append_periscope_image_html(parts, img, page_url, element)
            if len(text) > 20 and not _is_periscope_junk_text(text):
                key = text.lower()
                if key not in seen_text:
                    seen_text.add(key)
                    _append_periscope_text_html(parts, element.name, text)
            continue

        if element.name in ("ul", "ol"):
            items = [
                li.get_text(" ", strip=True)
                for li in element.find_all("li", recursive=False)
                if li.get_text(strip=True)
            ]
            if not items:
                continue
            tag = element.name
            lis = "".join(f"<li>{htmllib.escape(item)}</li>" for item in items)
            parts.append(f"<{tag}>{lis}</{tag}>")
            continue

        if element.name == "blockquote":
            if text and not _is_periscope_junk_text(text):
                parts.append(f"<blockquote>{htmllib.escape(text)}</blockquote>")
            continue

        if element.name in ("p", "h2", "h3", "h4") and text:
            key = text.lower()
            if key in seen_text:
                continue
            seen_text.add(key)
            _append_periscope_text_html(parts, element.name, text)

    if not parts:
        return None
    return "\n".join(parts)


def fetch_mag_m2a_page(url: str) -> BeautifulSoup | None:
    try:
        time.sleep(random.uniform(0.4, 1.0))
        resp = requests.get(url, impersonate="chrome110", timeout=25, allow_redirects=True)
        if resp.status_code != 200:
            return None
        return BeautifulSoup(resp.text, "html.parser")
    except Exception:
        return None


def _clean_mag_title(title: str | None) -> str | None:
    if not title:
        return None
    title = htmllib.unescape(title).strip()
    title = re.sub(r"\s*[-|]\s*m2a le mag\s*$", "", title, flags=re.I)
    title = re.sub(r"\s*[-|]\s*mulhouse alsace\s*$", "", title, flags=re.I)
    return title.strip() or None


def _extract_mag_content(soup: BeautifulSoup) -> str | None:
    content_div = (
        soup.find("div", class_="interne")
        or soup.find("div", class_="tribe-events-single-event-description")
        or soup.find("div", class_="tribe-events-content")
        or soup.find("div", class_="entry-content")
    )
    if not content_div:
        return None

    text_parts = []
    extrait = soup.find("p", class_="extrait")
    if extrait:
        text_parts.append(extrait.get_text().strip())

    for garbage in content_div.select(".important, .encadre, script, style, .sharedaddy"):
        garbage.decompose()

    body = content_div.get_text("\n", strip=True)
    if body:
        text_parts.append(body)

    if not text_parts:
        return None
    return "\n\n".join(dict.fromkeys(text_parts))


def parse_mag_m2a_article(soup: BeautifulSoup, url: str) -> dict:
    title = None
    description = None
    image_url = None
    image_caption = None
    published_at = None
    content = None

    og_title = soup.find("meta", property="og:title")
    if og_title and og_title.get("content"):
        title = _clean_mag_title(og_title["content"])

    og_desc = soup.find("meta", property="og:description")
    if og_desc and og_desc.get("content"):
        description = htmllib.unescape(og_desc["content"]).strip()

    og_image = soup.find("meta", property="og:image")
    if og_image and og_image.get("content"):
        image_url = htmllib.unescape(og_image["content"]).strip()

    pub_meta = soup.find("meta", property="article:published_time")
    if pub_meta and pub_meta.get("content"):
        published_at = _parse_iso_datetime(pub_meta["content"])

    for script in soup.find_all("script", type="application/ld+json"):
        try:
            raw = script.string
            if not raw:
                continue
            data = json.loads(raw.strip())
            items = data if isinstance(data, list) else [data]
            for item in items:
                if not isinstance(item, dict):
                    continue
                if item.get("@type") not in ("NewsArticle", "Article", "BlogPosting", "Event"):
                    continue
                if not title:
                    title = _clean_mag_title(str(item.get("headline") or item.get("name") or ""))
                if not description and item.get("description"):
                    description = htmllib.unescape(str(item["description"])).strip()
                if not published_at and item.get("datePublished"):
                    published_at = _parse_iso_datetime(str(item["datePublished"]))
                if not image_url:
                    image_url = _parse_mplusinfo_image(item.get("image"))
                break
        except (json.JSONDecodeError, TypeError):
            continue

    if not title:
        h1 = soup.find("h1")
        if h1:
            title = _clean_mag_title(h1.get_text(strip=True))

    content = _extract_mag_content(soup)
    if content:
        content = content.replace("\x00", "")

    if not image_caption:
        image_caption = extract_image_caption(soup, url, image_url)

    if not description and content:
        description = content[:300]

    return {
        "title": title,
        "description": description or "",
        "image_url": image_url,
        "image_caption": image_caption,
        "published_at": published_at,
        "content": content,
    }


def parse_periscope_article(soup: BeautifulSoup, url: str) -> dict:
    title = None
    description = None
    image_url = None
    image_caption = None
    published_at = None
    content = None

    og_title = soup.find("meta", property="og:title")
    if og_title and og_title.get("content"):
        title = _clean_periscope_title(og_title["content"])

    og_desc = soup.find("meta", property="og:description")
    if og_desc and og_desc.get("content"):
        description = htmllib.unescape(og_desc["content"]).strip()

    og_image = soup.find("meta", property="og:image")
    if og_image and og_image.get("content"):
        image_url = htmllib.unescape(og_image["content"]).strip()

    pub_meta = soup.find("meta", property="article:published_time")
    if pub_meta and pub_meta.get("content"):
        published_at = _parse_iso_datetime(pub_meta["content"])

    for script in soup.find_all("script", type="application/ld+json"):
        try:
            raw = script.string
            if not raw:
                continue
            data = json.loads(raw.strip())
            items = data if isinstance(data, list) else [data]
            for item in items:
                if not isinstance(item, dict):
                    continue
                if item.get("@type") not in ("NewsArticle", "Article", "WebPage", "BlogPosting"):
                    continue
                if not title:
                    title = _clean_periscope_title(str(item.get("headline") or item.get("name") or ""))
                if not description and item.get("description"):
                    description = htmllib.unescape(str(item["description"])).strip()
                if not published_at and item.get("datePublished"):
                    published_at = _parse_iso_datetime(str(item["datePublished"]))
                if not image_url:
                    image_url = _parse_mplusinfo_image(item.get("image"))
                break
        except (json.JSONDecodeError, TypeError):
            continue

    if not title:
        h1 = soup.find("h1")
        if h1:
            title = _clean_periscope_title(h1.get_text(strip=True))

    content = _extract_periscope_content(soup, url)
    if content:
        content = content.replace("\x00", "")

    if not image_caption:
        image_caption = extract_image_caption(soup, url, image_url)

    if not description and content:
        description = content[:300]

    return {
        "title": title,
        "description": description or "",
        "image_url": image_url,
        "image_caption": image_caption,
        "published_at": published_at,
        "content": content,
    }


def _absolutize_media_url(page_url: str, src: str | None) -> str | None:
    """Résout une URL d'image relative/absolue en URL exploitable.

    Filtre les placeholders/logos/pixels décoratifs.
    """
    if not src:
        return None
    src = src.strip()
    if not src or src.startswith("data:") or src.startswith("blob:"):
        return None
    if any(p in src.lower() for p in ("placeholder", "logo", "pixel", "loader", "favicon")):
        return None
    if src.startswith("//"):
        return f"https:{src}"
    if src.startswith("/"):
        from urllib.parse import urljoin

        return urljoin(page_url, src)
    if src.startswith("http"):
        return src
    return None


def _img_url_from_element(img) -> str | None:
    if not img:
        return None
    return (
        img.get("src")
        or img.get("data-src")
        or img.get("data-lazy-src")
        or img.get("data-original")
        or img.get("content")
    )


def _is_generic_image_src(url: str) -> bool:
    """Filtre les images décoratives/génériques souvent répétées."""
    lower = url.lower()
    if any(p in lower for p in (
        "logo", "banner", "bannierepub", "icon-", "/icons/", "sprite", "avatar", "pixel",
        "placeholder", "default", "background", "pattern", "advert", "pub-",
        "spacer", "tracking", "beacon", "bouton-pub", "partenaire",
    )):
        return True
    # Bannières publicitaires aux dimensions dédiées (jds-300x600, -970-250, …)
    if re.search(r"(jds|pub|banner|ad)-?\d{3,4}x\d{2,4}", lower):
        return True
    return False


def _upgrade_jds_url(url: str) -> str:
    """Passe les vignettes jds.fr (-260-260, -200-200) à la haute résolution.

    Les URLs jds.fr acceptent le suffixe -LARGEUR-HAUTEUR ; -1200-0 donne la
    version la plus grande dispo. On laisse les dimensions déjà grandes.
    """
    if "jds.fr/medias/image/" not in url:
        return url
    m = re.search(r"-(\d{3,4})-(\d{3,4})\.(webp|jpg|jpeg|png)$", url)
    if not m:
        return url
    w, h = int(m.group(1)), int(m.group(2))
    if w >= 800 or h >= 800:
        return url
    return re.sub(r"-\d{3,4}-\d{3,4}\.(webp|jpg|jpeg|png)$", "-1200-0.\\1", url)


def _dedupe_images(images: list) -> list:
    """Déduplique par URL normalisée (sans variantes de résolution)."""
    seen = set()
    out = []
    for img in images:
        key = _normalize_image_path(img["url"]) or img["url"]
        key = re.sub(r"(-\d{2,}){1,3}\.(webp|jpg|jpeg|png|gif)$", "", key)
        if key in seen:
            continue
        seen.add(key)
        out.append(img)
    return out


def _extract_ebra_images(soup: BeautifulSoup, page_url: str) -> list:
    """L'Alsace / DNA : figures mainImage (hero + texte).

    Chaque figure a un lien `a.chocolat-image[href]` vers la haute résolution
    (NW_raw) et la légende est dans le title du lien / l'alt de l'img.
    """
    images = []
    seen = set()

    for figure in soup.find_all("figure", class_="mainImage"):
        zoom = figure.find("a", class_="chocolat-image") or figure.find("a", href=True)
        src = None
        if zoom and zoom.get("href"):
            src = zoom["href"].strip()
        img = figure.find("img")
        if not src and img:
            src = _absolutize_media_url(page_url, _img_url_from_element(img))
        if not src:
            continue
        if _normalize_image_path(src) in seen:
            continue
        seen.add(_normalize_image_path(src))

        caption = None
        if zoom and zoom.get("title"):
            caption = _clean_caption(zoom.get("title").strip())
        if not caption and img and img.get("alt"):
            caption = _clean_caption(img["alt"].strip())
        if not caption:
            figcap = figure.find("figcaption")
            if figcap:
                caption = _clean_caption(figcap.get_text(" ", strip=True))

        is_hero = figure is soup.find("figure", class_="mainImage")
        images.append({"url": src, "caption": caption, "source": "hero" if is_hero else "gallery"})

    return images


def _extract_figure_images(soup: BeautifulSoup, page_url: str) -> list:
    """Extraction générique depuis les <figure> du corps (Periscope, M+, Mag…)."""
    images = []
    seen = set()
    article = soup.find("article") or soup.find("main") or soup
    for figure in article.find_all("figure"):
        img = figure.find("img")
        src = _absolutize_media_url(page_url, _img_url_from_element(img))
        if not src or _normalize_image_path(src) in seen:
            continue
        seen.add(_normalize_image_path(src))
        caption = None
        figcap = figure.find("figcaption")
        if figcap:
            caption = _clean_caption(figcap.get_text(" ", strip=True))
        images.append({"url": src, "caption": caption, "source": "gallery"})
    return images


def _extract_jds_images(soup: BeautifulSoup, page_url: str) -> list:
    """jds.fr : pas de galerie d'article exploitable.

    Le "carousel-contenu" et les blocs de la page contiennent des vignettes
    de suggestions/annonces sponsorisées (blindtest, quiz, billetterie…),
    pas les images de l'article. On ne retourne donc aucune image.
    """
    return []


def _extract_article_images(soup: BeautifulSoup, page_url: str) -> list:
    """Images d'articles génériques (img dans <article>/<main>)."""
    images = []
    seen = set()
    article = soup.find("article") or soup.find("main") or soup
    for img in article.find_all("img"):
        src = _absolutize_media_url(page_url, _img_url_from_element(img))
        if not src or _is_generic_image_src(src) or _normalize_image_path(src) in seen:
            continue
        src = _upgrade_jds_url(src)
        seen.add(_normalize_image_path(src))
        caption = None
        figcap = img.find_parent("figure")
        if figcap:
            fc = figcap.find("figcaption")
            if fc:
                caption = _clean_caption(fc.get_text(" ", strip=True))
        if not caption:
            alt = (img.get("alt") or "").strip()
            caption = _clean_caption(alt)
        images.append({"url": src, "caption": caption, "source": "gallery"})
    if not images:
        images.extend(_extract_figure_images(soup, page_url))
    return images


def extract_article_images(
    soup: BeautifulSoup,
    url: str,
    image_url: str | None = None,
    image_caption: str | None = None,
) -> list:
    """Extrait TOUTES les images d'un article avec leurs légendes.

    Retourne une liste de dicts : {"url", "caption", "source"}.
    L'image principale (image_url) est toujours placée en premier.
    """
    if is_ebra_url(url):
        images = _extract_ebra_images(soup, url)
    elif is_jds_url(url):
        images = _extract_jds_images(soup, url)
    else:
        images = _extract_article_images(soup, url)

    if image_url:
        hero = {"url": image_url, "caption": image_caption, "source": "hero"}
        images = [hero] + [
            i for i in images if _normalize_image_path(i["url"]) != _normalize_image_path(image_url)
        ]

    return _dedupe_images(images)