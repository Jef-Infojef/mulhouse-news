import os
import requests
import psycopg2
from bs4 import BeautifulSoup
from dotenv import load_dotenv

# Configuration
def load_env():
    root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    for f in [".envenv", ".env.local", ".env"]:
        path = os.path.join(root_dir, f)
        if os.path.exists(path):
            load_dotenv(path)
            if os.environ.get("DATABASE_URL"): return True
    return False

load_env()
DATABASE_URL = os.environ.get("DATABASE_URL")

COOKIES_RAW = ".XCONNECT_SESSION=2=42F647DB9B788CF4E0AFFF1DD52DE98DAC09560B7B8173B6AE707DE13249B5D3D98E26C37209690D989A05961C1E93CBDDF2909ED6FF95194BEA6AE2C1E5A62F519DB83384CA795ACE1E2824AA4C1D00C904F51699D03E6489E9A4B4C8211E0D25B9B66E68555AA3B098E18D1CFB0D8E55CD162A101CF8E23306F0A225ABBE4E6AA1480CEA97DAEF016F99185FECA69B74DCE53DE2A59FB8889A43374A7891008D274391E153481FAF94E8CF51E25A9872DE0D0AA146142A059E319D5BEC9708926A8C25B1A97FBA849A2B64CC973B6CE3700E3E16AB420B9135DE775FE8D9E4AF4D143969441F03400814963FB3C265; .XCONNECTKeepAlive=2=1; .XCONNECT=2=1; _poool=9aab6ee3-fda6-43fc-a90e-29de3c73d8f7"

cookies = {}
for part in COOKIES_RAW.split(';'):
    if '=' in part:
        key, value = part.strip().split('=', 1)
        cookies[key] = value

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
    'Accept-Language': 'fr-FR,fr;q=0.9',
    'Referer': 'https://www.lalsace.fr/',
}

def get_db_connection():
    url = DATABASE_URL
    if url and "?pgbouncer=true" in url: url = url.replace("?pgbouncer=true", "")
    return psycopg2.connect(url)

def test_one():
    session = requests.Session()
    session.headers.update(headers)
    for key, value in cookies.items():
        session.cookies.set(key, value, domain=".lalsace.fr")

    conn = get_db_connection()
    cur = conn.cursor()
    
    cur.execute("""
        SELECT id, title, link 
        FROM \"Article\" 
        WHERE source ILIKE '%Alsace%' AND content IS NULL
          AND \"publishedAt\" >= '2025-10-01' AND \"publishedAt\" < '2025-11-01'
        LIMIT 1
    """)
    article = cur.fetchone()
    if not article:
        print("Aucun article trouvé.")
        return

    art_id, title, link = article
    print(f"[*] Test sur : {title}")
    print(f"[*] Lien : {link}")
    
    try:
        response = session.get(link, timeout=15)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Suppression de la modale de connexion bruyante
        for modal in soup.find_all(class_='GXCO_content'):
            modal.decompose()

        text_parts = []
        
        # Chapô
        chapo = soup.find(class_='chapo') or soup.find(class_='article__chapo')
        if chapo: text_parts.append(chapo.get_text().strip())

        # Blocs de texte (textComponent)
        content_blocks = soup.find_all('div', class_='textComponent')
        if content_blocks:
            for block in content_blocks:
                txt = block.get_text("\n", strip=True)
                if txt and len(txt) > 10:
                    text_parts.append(txt)

        full_text = "\n\n".join(text_parts)
        print("\n=== CONTENU RÉCUPÉRÉ ===\n")
        print(full_text[:2000] + ("..." if len(full_text) > 2000 else ""))
        print("\n========================\n")
        print(f"Longueur : {len(full_text)} caractères")

    except Exception as e:
        print(f"Erreur : {e}")
    finally:
        cur.close()
        conn.close()

if __name__ == "__main__":
    test_one()
