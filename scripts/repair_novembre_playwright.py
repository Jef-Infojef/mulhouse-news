import os
import asyncio
from playwright.async_api import async_playwright
import psycopg2
from dotenv import load_dotenv
import random

load_dotenv(".env.local")
DATABASE_URL = os.environ.get("DATABASE_URL")

async def scrape_article(browser_context, url):
    page = await browser_context.new_page()
    
    # On bloque les pubs et trackers pour accélérer et éviter les timeouts
    await page.route("**/*", lambda route: 
        route.abort() if any(x in route.request.url for x in [
            "google-analytics", "doubleclick", "googlesyndication", "taboola", 
            "outbrain", "facebook", "amazon-adsystem", "adnxs", "smartadserver"
        ]) else route.continue_()
    )

    try:
        print(f"[*] Chargement de : {url}")
        # On attend seulement 'domcontentloaded' au lieu de 'networkidle'
        await page.goto(url, wait_until="domcontentloaded", timeout=30000)
        
        # On attend que le sélecteur principal apparaisse
        try:
            await page.wait_for_selector(".col_main, .article__chapo", timeout=10000)
        except:
            pass # On continue quand même
            
        await asyncio.sleep(2) # Petit délai pour le rendu
        
        # Extraction du texte complet
        content = await page.evaluate("""() => {
            let texts = [];
            let elements = document.querySelectorAll('.chapo, .article__chapo, .textComponent p, .paywall2 p, .article-content p');
            elements.forEach(el => {
                let t = el.innerText.trim();
                if (t.length > 25) {
                    // On évite les doublons de paragraphes
                    if (!texts.some(existing => existing.substring(0, 30) === t.substring(0, 30))) {
                        texts.push(t);
                    }
                }
            });
            return texts.join('\n\n');
        }""")
        
        return content
    except Exception as e:
        print(f"    [!] Erreur: {e}")
        return None
    finally:
        await page.close()

async def main():
    clean_url = DATABASE_URL.replace("?pgbouncer=true", "").replace("&pgbouncer=true", "")
    conn = psycopg2.connect(clean_url)
    cur = conn.cursor()

    cur.execute("""
        SELECT id, title, link 
        FROM \"Article\" 
        WHERE source ILIKE '%Alsace%' 
          AND \"publishedAt\" >= '2025-11-01' AND \"publishedAt\" < '2025-12-01'
          AND (content IS NULL OR LENGTH(content) < 500)
        ORDER BY \"publishedAt\" DESC
        LIMIT 50
    """)
    articles = cur.fetchall()
    
    if not articles:
        print("Aucun article à traiter.")
        return

    print(f"[*] Playwright (Mode Rapide) va traiter {len(articles)} articles.")

    async with async_playwright() as p:
        user_data_dir = os.path.join(os.environ["USERPROFILE"], "AppData", "Local", "Google", "Chrome", "User Data")
        
        # On lance Chrome avec les protections anti-détection
        browser = await p.chromium.launch_persistent_context(
            user_data_dir,
            headless=True,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-setuid-sandbox"
            ]
        )

        for art_id, title, link in articles:
            print(f"-> {title[:50]}...")
            full_text = await scrape_article(browser, link)
            
            if full_text and len(full_text) > 400:
                cur.execute('UPDATE \"Article\" SET content = %s WHERE id = %s', (full_text, art_id))
                conn.commit()
                print(f"   ✅ OK ({len(full_text)} chars)")
            else:
                print(f"   ⚠️ Échec ou contenu trop court ({len(full_text) if full_text else 0}).")
            
            await asyncio.sleep(random.uniform(1, 2))

        await browser.close()

    cur.close()
    conn.close()

if __name__ == "__main__":
    asyncio.run(main())