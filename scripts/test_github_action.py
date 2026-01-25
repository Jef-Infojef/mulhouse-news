import os
import requests
import psycopg2
from bs4 import BeautifulSoup
import json

def load_config():
    db_url = os.environ.get("DATABASE_URL")
    cookies_raw = os.environ.get("ALSACE_COOKIES")
    return db_url, cookies_raw

def fetch_content(session, url):
    print(f"[*] Fetching: {url}")
    try:
        resp = session.get(url, timeout=20)
        page_text = resp.text
        
        # Analyse des marqueurs de connexion
        # Sur L'Alsace, un abonné voit son pseudo ou "Déconnexion"
        is_connected = any(x in page_text for x in ["Se déconnecter", "Mon compte", "Mon profil", "suscriber"])
        
        print(f"[*] État session GitHub : {'✅ CONNECTÉ' if is_connected else '❌ NON CONNECTÉ'}")
        
        if not is_connected:
            # On cherche si on voit "S'abonner pour lire la suite"
            if "abonnez-vous" in page_text.lower() or "paywall" in page_text.lower():
                print("   ⚠️ Paywall détecté : GitHub est vu comme un visiteur gratuit.")

        soup = BeautifulSoup(page_text, 'html.parser')
        text_parts = []
        
        # Extraction
        chapo = soup.find(class_='chapo') or soup.find(class_='article__chapo')
        if chapo: text_parts.append(chapo.get_text().strip())
        
        content_blocks = soup.find_all('div', class_='textComponent')
        for block in content_blocks:
            txt = block.get_text("\n", strip=True)
            if len(txt) > 10: text_parts.append(txt)
            
        if not text_parts:
            # Fallback JSON
            for script in soup.find_all('script', type='application/ld+json'):
                try:
                    data = json.loads(script.string)
                    items = data if isinstance(data, list) else [data]
                    for item in items:
                        if item.get('@type') in ['VideoObject', 'NewsArticle'] and item.get('description'):
                            text_parts.append(item['description'].strip())
                except: pass

        return "\n\n".join(text_parts)
    except Exception as e:
        print(f"❌ Erreur fetch : {e}")
        return None

def main():
    print("=== TEST SCRAPER GITHUB ACTIONS V9 ===")
    db_url, cookies_raw = load_config()
    if not db_url: return

    session = requests.Session()
    # User-Agent très récent
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
        'Accept-Language': 'fr-FR,fr;q=0.9,en-US;q=0.8',
    })
    
    if cookies_raw:
        # Nettoyage et affichage de contrôle (sécurisé)
        clean_raw = cookies_raw.strip().replace('"', '').replace("'", "")
        print(f"[*] Analyse du secret : {clean_raw[:10]}...{clean_raw[-10:]} (Total: {len(clean_raw)} chars)")
        
        # On essaie de parser les cookies s'ils sont au format "Nom=Valeur; Nom2=Valeur2"
        # Ou de forcer .XCONNECT_SESSION si c'est juste la valeur brute
        if '=' not in clean_raw[:50]:
            session.cookies.set(".XCONNECT_SESSION", clean_raw, domain=".lalsace.fr")
        else:
            parts = [p.strip() for p in clean_raw.split(';') if '=' in p]
            for p in parts:
                k, v = p.split('=', 1)
                session.cookies.set(k.strip(), v.strip(), domain=".lalsace.fr")
        
        # Ajout d'un cookie de consentement Didomi simulé (souvent requis)
        session.cookies.set("eu-consent", "true", domain=".lalsace.fr")
        print(f"[*] Cookies en session : {', '.join(session.cookies.get_dict().keys())}")

    # Test sur l'article de 4ko
    test_link = "https://www.lalsace.fr/insolite/2026/01/25/course-d-orientation-quand-l-histoire-industrielle-se-decouvre-un-plan-et-une-boussole-a-la-main"
    content = fetch_content(session, test_link)
    
    if content:
        print(f"✅ RÉSULTAT : {len(content)} caractères.")
        if len(content) > 3000:
            print("🚀 SUCCÈS TOTAL SUR GITHUB !")
        else:
            print(f"⚠️ TRONQUÉ : {len(content)}/3927 chars.")
    else:
        print("❌ ÉCHEC : Vide.")

if __name__ == "__main__":
    main()