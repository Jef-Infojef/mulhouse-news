"""Utilitaires partagés entre les scripts de scraping."""
import html as htmllib
import json
import re
import time
import random
from bs4 import BeautifulSoup
from curl_cffi import requests

EBRA_DOMAINS = ("lalsace.fr", "dna.fr", "estrepublicain.fr", "vosgesmatin.fr")


def is_ebra_url(url: str) -> bool:
    return any(d in url for d in EBRA_DOMAINS)


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


def extract_image_caption(soup: BeautifulSoup, url: str, image_url: str | None = None) -> str | None:
    """Extrait la légende de la photo principale (ou description vidéo)."""
    if "/video" in url.lower():
        video_caption = _extract_video_caption(soup)
        if video_caption:
            return video_caption

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
) -> str | None:
    """Télécharge la page et extrait uniquement la légende image."""
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
            return None
        soup = BeautifulSoup(resp.text, "html.parser")
        return extract_image_caption(soup, target_url, image_url)
    except Exception:
        return None