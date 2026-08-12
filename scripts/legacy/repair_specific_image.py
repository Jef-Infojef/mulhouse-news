
import os
import json
import time
from bs4 import BeautifulSoup
from curl_cffi import requests
from prisma import Prisma
import asyncio

async def repair_specific_image():
    db = Prisma()
    await db.connect()

    url = 'https://www.lalsace.fr/culture-loisirs/2026/01/28/on-fait-quoi-ce-week-end-du-30-janvier-au-1er-fevrier-dans-le-sud-alsace'
    print(f"Tentative de récupération d'image pour : {url}")

    try:
        resp = requests.get(url, impersonate="chrome110", timeout=30)
        if resp.status_code != 200:
            print(f"Erreur HTTP: {resp.status_code}")
            return

        soup = BeautifulSoup(resp.text, 'html.parser')
        
        # 1. Chercher dans les balises Open Graph
        og_image = soup.find("meta", property="og:image")
        image_url = og_image["content"] if og_image else None

        # 2. Chercher dans Twitter Cards
        if not image_url:
            twitter_image = soup.find("meta", name="twitter:image")
            image_url = twitter_image["content"] if twitter_image else None

        # 3. Chercher dans LD+JSON
        if not image_url:
            for script in soup.find_all('script', type='application/ld+json'):
                try:
                    data = json.loads(script.string.strip())
                    if isinstance(data, list): data = data[0]
                    if 'image' in data:
                        if isinstance(data['image'], dict): image_url = data['image'].get('url')
                        else: image_url = data['image']
                        break
                except: pass

        if image_url:
            print(f"✅ Image trouvée : {image_url}")
            # Mise à jour en base
            await db.article.update(
                where={'link': url},
                data={'imageUrl': image_url}
            )
            print("Base de données mise à jour.")
        else:
            print("❌ Aucune image trouvée sur la page.")

    except Exception as e:
        print(f"Erreur : {e}")
    finally:
        await db.disconnect()

if __name__ == '__main__':
    asyncio.run(repair_specific_image())
