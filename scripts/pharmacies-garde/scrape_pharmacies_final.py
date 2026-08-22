#!/usr/bin/env python3
"""
Scraper pharmacies de garde avec 2captcha
Résout automatiquement les CAPTCHAs popups
"""

import json
import os
import shutil
import subprocess
import sys
import time
import logging
import re
from datetime import datetime
from pathlib import Path

import requests
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout
from bs4 import BeautifulSoup
from twocaptcha import TwoCaptcha

# Configuration
CONFIG = {
    "url": "https://www.3237.fr/",
    "code_postal": "68100",
    "ville": "MULHOUSE",
    "api_url": os.getenv("API_URL", "http://localhost:3000/api/pharmacies-garde"),
    "api_key": os.getenv("PHARMACIES_API_KEY", ""),
    "captcha_api_key": os.getenv("CAPTCHA_API_KEY", ""),
    "headless": os.getenv("HEADLESS", "false").lower() == "true",
    "log_file": Path(__file__).parent / "scraper_final.log",
}

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(CONFIG["log_file"], encoding="utf-8"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


def random_delay(min_ms=100, max_ms=500):
    """Délai aléatoire"""
    import random
    time.sleep(random.randint(min_ms, max_ms) / 1000)


def solve_recaptcha_v2_with_2captcha(page, api_key, page_url, sitekey):
    """
    Résout ReCAPTCHA v2 via 2captcha en utilisant la méthode standard
    Recommandée par 2captcha: https://2captcha.com/h/how-to-bypass-google-recaptcha

    Args:
        page: page Playwright
        api_key: clé API 2captcha
        page_url: URL de la page
        sitekey: sitekey ReCAPTCHA

    Returns:
        str: Token gRecaptchaResponse ou None si erreur
    """
    logger.info("Résolution ReCAPTCHA v2 via 2captcha (méthode standard)...")

    try:
        # Vérifier le solde
        solver = TwoCaptcha(api_key)
        try:
            balance = solver.balance()
            logger.info(f"Solde 2captcha: ${balance:.4f}")
        except Exception as e:
            logger.warning(f"Impossible de vérifier le solde: {e}")

        # Envoyer à 2captcha avec la sitekey
        logger.info(f"Envoi à 2captcha...")
        logger.info(f"  URL: {page_url}")
        logger.info(f"  Sitekey: {sitekey}")

        result = solver.recaptcha(
            sitekey=sitekey,
            url=page_url,
            version='v2'
        )

        if not result or 'code' not in result:
            logger.warning("2captcha retourné résultat invalide")
            return None

        token = result['code']
        logger.info(f"✅ Token reçu: {token[:50]}...")
        return token

    except Exception as e:
        logger.error(f"Erreur 2captcha ReCAPTCHA v2: {e}")
        return None


def inject_recaptcha_token(page, token):
    """
    Injecte le token ReCAPTCHA dans la page via JavaScript
    Méthode directe sans timeout (plus rapide)
    """
    logger.info("Injection du token ReCAPTCHA...")

    try:
        # Injection JavaScript directe (pas de timeout comme .fill())
        logger.info("  Injection JavaScript...")
        page.evaluate(f"""
            if (window.document.querySelector('textarea[name="g-recaptcha-response"]')) {{
                window.document.querySelector('textarea[name="g-recaptcha-response"]').value = '{token}';
            }}
            if (window.document.getElementById('g-recaptcha-response')) {{
                window.document.getElementById('g-recaptcha-response').value = '{token}';
            }}
        """)
        logger.info("  ✓ Token injecté")
        return True

    except Exception as e:
        logger.error(f"Erreur injection token: {e}")
        return False


def scrape_once(page):
    """Une tentative complète de scraping"""
    pharmacies = []

    try:
        logger.info("Navigation vers 3237.fr...")
        page.goto(CONFIG["url"], wait_until="networkidle", timeout=30000)
        random_delay(1000, 1500)

        # Accepter les cookies
        logger.info("Acceptation des cookies...")
        try:
            accept_selectors = ["text=J'accepte", "button:has-text('Accepter')"]
            for selector in accept_selectors:
                try:
                    btn = page.locator(selector).first
                    if btn.count() > 0:
                        btn.click(timeout=2000)
                        random_delay(500, 800)
                        break
                except Exception:
                    continue
        except Exception as e:
            logger.warning(f"Acceptation cookies échouée: {e}")

        # Créer le cookie par sécurité
        try:
            page.evaluate("document.cookie = 'ResoConsentCaptcha=true; path=/; max-age=31536000';")
            logger.info("Cookie créé")
        except Exception:
            pass

        # Saisir code postal
        logger.info(f"Saisie code postal: {CONFIG['code_postal']}")
        cp_input = page.locator("input[name='cp']").first
        try:
            cp_input.click(timeout=3000)
        except Exception:
            page.evaluate("document.querySelector('input[name=\"cp\"]').focus()")
            random_delay(300, 500)

        cp_input.fill("")
        cp_input.type(CONFIG["code_postal"], delay=50)
        random_delay(300, 500)

        # Gestion ReCAPTCHA v2 avec 2captcha
        logger.info("Gestion ReCAPTCHA v2...")

        if not CONFIG["captcha_api_key"]:
            logger.error("2captcha API key manquante!")
            return None

        # Sitekey ReCAPTCHA sur 3237.fr
        recaptcha_sitekey = "6LeAik0qAAAAABf8voEDQnYy149TvJjZMclDb-fV"

        # Résoudre ReCAPTCHA v2 via 2captcha (méthode standard recommandée)
        token = solve_recaptcha_v2_with_2captcha(
            page=page,
            api_key=CONFIG["captcha_api_key"],
            page_url=page.url,
            sitekey=recaptcha_sitekey
        )

        if not token:
            logger.error("Impossible de résoudre ReCAPTCHA v2")
            return None

        # Injecter le token dans la page
        if not inject_recaptcha_token(page, token):
            logger.error("Impossible d'injecter le token")
            return None

        # Attendre un peu pour que Google process le token
        random_delay(1000, 2000)

        # Cliquer bouton recherche
        logger.info("Soumission du formulaire...")
        try:
            btn = page.locator("input[type='submit']").first
            if btn.count() > 0:
                btn.click()
        except Exception:
            page.keyboard.press("Enter")

        random_delay(2000, 3000)
        try:
            page.wait_for_load_state("networkidle", timeout=15000)
        except PlaywrightTimeout:
            logger.warning("Timeout navigation")

        # Sélection ville
        logger.info(f"Sélection ville: {CONFIG['ville']}")
        try:
            ville_link = page.locator(f"text={CONFIG['ville']}")
            if ville_link.count() > 0:
                ville_link.first.click()
                random_delay(1000, 2000)
                page.wait_for_load_state("networkidle", timeout=15000)
        except Exception as e:
            logger.warning(f"Sélection ville échouée: {e}")

        # Sélection heure
        logger.info("Sélection heure...")
        try:
            # Chercher un radio button heure_saisie (prendre le premier disponible)
            radio = page.locator("input[name='heure_saisie']").first
            if radio and radio.count() > 0:
                logger.info("Radio button trouvé, clic...")
                radio.click()
                random_delay(500, 1000)

                # Cliquer le bouton Valider
                btn = page.locator("input[type='submit']").first
                if btn and btn.count() > 0:
                    logger.info("Clic sur Valider...")
                    btn.click()
                    random_delay(1000, 2000)
                    logger.info("Attente chargement page pharmacies...")
                    page.wait_for_load_state("networkidle", timeout=15000)
                    logger.info("Page pharmacies chargée!")
            else:
                logger.warning("Aucun radio button heure_saisie trouvé")
        except Exception as e:
            logger.warning(f"Sélection heure échouée: {e}")
            import traceback
            logger.warning(traceback.format_exc())

        # Extraction pharmacies
        logger.info("Extraction des pharmacies...")
        content = page.content()

        # Sauvegarder le HTML pour debug
        html_path = CONFIG["log_file"].parent / "page_final.html"
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(content)
        logger.info(f"HTML sauvegardé: {html_path.name}")

        soup = BeautifulSoup(content, "html.parser")

        pharmacy_names = soup.find_all("font", color="#FF6600")
        logger.info(f"Pharmacies trouvées: {len(pharmacy_names)}")

        # Debug: chercher d'autres patterns
        if len(pharmacy_names) == 0:
            logger.warning("Aucune pharmacie avec color=#FF6600 - cherche alternatives...")
            all_fonts = soup.find_all("font")
            logger.info(f"Total fonts trouvées: {len(all_fonts)}")
            for i, font in enumerate(all_fonts[:10]):
                logger.info(f"  Font {i}: {font.get('color')} = {font.get_text(strip=True)[:50]}")

        for pharma_elem in pharmacy_names:
            try:
                pharma_name = pharma_elem.get_text(strip=True)
                if not pharma_name or len(pharma_name) < 2:
                    continue

                # Filtrer les commissariats et gendarmeries qui peuvent apparaître
                if any(x in pharma_name.upper() for x in ["COMMISSARIAT", "GENDARMERIE", "POLICE"]):
                    logger.info(f"Ignoré (non pharmacie): {pharma_name}")
                    continue

                address = None
                phone = None
                start_time = None
                end_time = None

                table = pharma_elem.find_parent("table")
                if table:
                    # Chercher l'adresse (color #003466)
                    addr_fonts = table.find_all("font", color="#003466")
                    if addr_fonts:
                        address = addr_fonts[0].get_text(strip=True)

                    # Chercher le téléphone
                    for para in table.find_all("p"):
                        text = para.get_text(strip=True)
                        if "TEL" in text:
                            phone = text.replace("TEL. :", "").replace("TEL :", "").strip()
                            break

                    # Chercher les horaires (format: "XXH à XXH")
                    for b_tag in table.find_all("b"):
                        text = b_tag.get_text(strip=True)
                        if "H" in text and "à" in text:
                            # Parser "14H à 08H" → startTime: 14, endTime: 08
                            try:
                                parts = text.split("à")
                                if len(parts) == 2:
                                    start_str = parts[0].strip().replace("H", "").strip()
                                    end_str = parts[1].strip().replace("H", "").strip()
                                    start_time = f"{int(start_str):02d}:00"
                                    end_time = f"{int(end_str):02d}:00"
                            except:
                                pass
                            break

                if pharma_name:
                    pharmacy_data = {
                        "name": pharma_name,
                        "address": address,
                        "phone": phone,
                        "startTime": start_time,
                        "endTime": end_time,
                        "isNightGuard": False,  # À déterminer par logic
                        "isWeekend": False,  # À déterminer par logic
                    }
                    pharmacies.append(pharmacy_data)
                    logger.info(f"Pharmacie extraite: {pharma_name} | {address or 'Adresse inconnue'} | {phone or 'Téléphone inconnu'}")

            except Exception as e:
                logger.debug(f"Erreur extraction: {e}")
                continue

        logger.info(f"Total extraites: {len(pharmacies)}")
        return pharmacies

    except Exception as e:
        logger.error(f"Erreur scraping: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return None


def save_pharmacies(pharmacies):
    """Enregistre en BDD via script Node (GH Actions) ou API Vercel (fallback local)."""
    payload = {
        "pharmacies": pharmacies,
        "code_postal": CONFIG["code_postal"],
        "ville": CONFIG["ville"],
        "scrape_date": datetime.now().isoformat(),
    }

    use_direct_db = bool(
        os.getenv("TURSO_DATABASE_URL")
        or os.getenv("DATABASE_URL")
        or os.getenv("SAVE_DIRECT_DB", "").lower() == "true"
    )

    if use_direct_db:
        repo_root = Path(__file__).resolve().parent.parent.parent
        payload_path = CONFIG["log_file"].parent / "pharmacies_payload.json"
        with open(payload_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False)

        logger.info(f"Enregistrement direct en BDD via {repo_root / 'scripts/pharmacies-save.ts'}")
        # npx.cmd sous Windows : shutil.which résout le chemin complet
        npx = shutil.which("npx") or "npx"
        result = subprocess.run(
            [npx, "tsx", "scripts/pharmacies-save.ts", str(payload_path)],
            cwd=repo_root,
            env=os.environ.copy(),
            capture_output=True,
            text=True,
            timeout=120,
        )
        if result.stdout:
            logger.info(result.stdout.strip())
        if result.returncode != 0:
            logger.error(f"Échec enregistrement direct (code {result.returncode})")
            if result.stderr:
                logger.error(result.stderr.strip())
            return False
        logger.info("✅ Données sauvegardées en BDD (sans Vercel)")
        return True

    if CONFIG["api_url"] and CONFIG["api_key"]:
        logger.info(f"Envoi vers API {CONFIG['api_url']}")
        try:
            headers = {"X-API-Key": CONFIG["api_key"]}
            response = requests.post(CONFIG["api_url"], json=payload, headers=headers, timeout=30)
            logger.info(f"API response: {response.status_code}")
            if response.status_code == 200:
                logger.info("✅ Succès! Données sauvegardées via API")
                return True
            logger.error(f"Erreur API: {response.text}")
        except Exception as e:
            logger.error(f"Erreur envoi API: {e}")
        return False

    logger.error("Aucun mode de sauvegarde configuré (TURSO_DATABASE_URL ou API_URL)")
    return False


def main():
    logger.info("="*60)
    logger.info(f"Démarrage - {datetime.now()}")
    logger.info("="*60)

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=CONFIG["headless"],
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-dev-shm-usage",
            ],
        )

        try:
            context = browser.new_context(
                locale="fr-FR",
                timezone_id="Europe/Paris",
            )
            page = context.new_page()

            result = scrape_once(page)

            if result and len(result) > 0:
                logger.info(f"Succès! {len(result)} pharmacies extraites")
                if not save_pharmacies(result):
                    sys.exit(1)
            else:
                logger.warning("Aucune pharmacie extraite")

        finally:
            try:
                context.close()
            except:
                pass
            try:
                browser.close()
            except:
                pass


if __name__ == "__main__":
    main()
