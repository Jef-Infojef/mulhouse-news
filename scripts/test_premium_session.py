import os
import psycopg2
import json
from curl_cffi import requests
from dotenv import load_dotenv

# Charger les variables d'environnement pour la DB
load_dotenv(".env")
load_dotenv(".envenv")

DATABASE_URL = os.environ.get("DATABASE_URL")

def get_app_config(conn, key):
    try:
        with conn.cursor() as cur:
            cur.execute('SELECT value FROM "AppConfig" WHERE key = %s', (key,))
            row = cur.fetchone()
            return row[0] if row else None
    except Exception as e:
        print(f"❌ Erreur lecture DB: {e}")
        return None

def test_session():
    print("--- TEST SESSION PREMIUM L'ALSACE ---")
    
    if not DATABASE_URL:
        print("❌ DATABASE_URL manquante.")
        return

    try:
        conn = psycopg2.connect(DATABASE_URL.replace("?pgbouncer=true", ""))
        cookie_value = get_app_config(conn, "EBRA_COOKIE")
        
        if not cookie_value:
            print("❌ Aucun cookie EBRA_COOKIE trouvé dans la table AppConfig.")
            return

        print(f"[*] Cookie trouvé en base: {cookie_value[:30]}...")
        
        # Nettoyage comme dans le scraper
        clean = cookie_value.strip().replace('"', '').replace("'", "")
        if ':' in clean: clean = clean.split(':', 1)[1].strip()
        if clean.startswith('2='): clean = clean[2:] # On garde juste la partie après 2=
        
        cookies_dict = {
            ".XCONNECT_SESSION": f"2={clean}",
            ".XCONNECTKeepAlive": "2=1",
            ".XCONNECT": "2=1",
            "_poool": "9aab6ee3-fda6-43fc-a90e-29de3c73d8f7"
        }

        # 1. Test de connexion
        print("[*] Test de connexion sur la home...")
        resp = requests.get(
            "https://www.lalsace.fr/", 
            cookies=cookies_dict,
            impersonate="chrome110",
            timeout=30
        )
        
        is_connected = any(x in resp.text for x in ["Se déconnecter", "Mon compte", "Mon profil", "Abonné"])
        print(f"[*] Statut connexion: {'✅ CONNECTÉ' if is_connected else '❌ NON CONNECTÉ'}")

        # 2. Test sur un article premium récent
        with conn.cursor() as cur:
            cur.execute('SELECT link, title FROM "Article" WHERE source ILIKE %s ORDER BY "publishedAt" DESC LIMIT 1', ('%Alsace%',))
            art = cur.fetchone()
            
        if art:
            link, title = art
            print(f"[*] Test sur l'article: {title}")
            print(f"[*] Lien: {link}")
            
            resp_art = requests.get(link, cookies=cookies_dict, impersonate="chrome110", timeout=30)
            
            # Un article complet contient la classe 'textComponent' plusieurs fois
            has_content = resp_art.text.count('textComponent') >= 2
            content_length = len(resp_art.text)
            
            print(f"[*] Taille HTML reçu: {content_length} octets")
            print(f"[*] Contenu complet détecté: {'✅ OUI' if has_content else '❌ NON (Paywall probable)'}")
            
            if not has_content and is_connected:
                print("\n[!] Analyse: Vous êtes connecté mais le contenu est quand même bloqué.")
                print("[!] Essayez de copier le header 'Cookie' complet depuis votre navigateur.")
        
        conn.close()

    except Exception as e:
        print(f"❌ Erreur critique: {e}")

if __name__ == "__main__":
    test_session()
