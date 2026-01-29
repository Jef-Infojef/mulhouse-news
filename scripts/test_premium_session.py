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
        
        db_session = get_app_config(conn, "EBRA_SESSION")
        db_poool = get_app_config(conn, "EBRA_POOOL")
        
        if not db_session:
            print("⚠️ EBRA_SESSION non trouvé, tentative avec l'ancien EBRA_COOKIE...")
            db_session = get_app_config(conn, "EBRA_COOKIE")
        
        if not db_session:
            print("❌ Aucune session trouvée.")
            return

        # Nettoyage session
        s_val = db_session.strip().replace('"', '').replace("'", "")
        if "2=" in s_val:
            s_val = s_val[s_val.find("2="):].split(";")[0]
        
        # Nettoyage poool
        p_val = db_poool.strip().replace('"', '').replace("'", "") if db_poool else "9aab6ee3-fda6-43fc-a90e-29de3c73d8f7"
        if "_poool=" in p_val:
            p_val = p_val.split("_poool=")[1].split(";")[0]

        print(f"[*] Session: {s_val[:20]}...")
        print(f"[*] Poool:   {p_val[:20]}...")
        
        cookies_dict = {
            ".XCONNECT_SESSION": s_val,
            ".XCONNECTKeepAlive": "2=1",
            ".XCONNECT": "2=1",
            "_poool": p_val
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

        # 2. Test sur un article premium spécifique
        target_article = "https://www.lalsace.fr/culture-loisirs/2026/01/28/affaire-des-vols-au-musee-de-l-impression-sur-etoffes-il-n-y-aura-pas-de-proces-avant-2027"
        print(f"[*] Test spécifique sur l'article: {target_article}")
        
        resp_art = requests.get(target_article, cookies=cookies_dict, impersonate="chrome110", timeout=30)
        
        # Un article complet contient la classe 'textComponent' plusieurs fois
        has_content = resp_art.text.count('textComponent') >= 2
        content_length = len(resp_art.text)
        
        print(f"[*] Taille HTML reçu: {content_length} octets")
        print(f"[*] Contenu complet détecté: {'✅ OUI' if has_content else '❌ NON (Paywall probable)'}")
        
        if not has_content:
            # Vérification si le chapô est présent
            if 'article__chapo' in resp_art.text or 'chapo' in resp_art.text:
                print("[!] Seul le chapô semble accessible.")
            
            if is_connected:
                print("\n[!] Analyse: Vous êtes connecté mais le contenu de CET article est bloqué.")
                print("[!] Cela arrive si l'article est ultra-récent ou a une protection spécifique.")
        
        conn.close()

    except Exception as e:
        print(f"❌ Erreur critique: {e}")

if __name__ == "__main__":
    test_session()
