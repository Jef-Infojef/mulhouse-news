import fs from 'fs';
import path from 'path';
import * as convex from './convex_client_ts';

// Phase 4 : accès DB portés Prisma → Convex (scripts/convex_client_ts.ts).
// La logique réseau (téléchargement, extensions, temps limite) est inchangée.
// Les noms de fichiers restent basés sur `supabaseId` (ex-cuid Prisma) pour
// les articles : stabilité des clés B2 et des valeurs localImage existantes.
// Les images de galerie n'ont pas d'UUID Supabase propre chez Convex : nom
// `gal-<_id Convex>`.

const IMAGE_DIR = path.join(process.cwd(), 'public', 'article-images');

if (!fs.existsSync(IMAGE_DIR)) {
  fs.mkdirSync(IMAGE_DIR, { recursive: true });
}

async function getExtensionFromContentType(contentType: string | null): Promise<string> {
  if (!contentType) return 'jpg';
  const ct = contentType.toLowerCase();
  if (ct.includes('image/png')) return 'png';
  if (ct.includes('image/webp')) return 'webp';
  if (ct.includes('image/gif')) return 'gif';
  if (ct.includes('image/svg+xml')) return 'svg';
  if (ct.includes('image/avif')) return 'avif';
  return 'jpg';
}

async function downloadImage(url: string, id: string, articleLink?: string): Promise<string | null> {
  try {
    let finalUrl = url.trim();

    if (finalUrl === 'image.png' || finalUrl === 'undefined' || !finalUrl || finalUrl.includes('placeholder.jpg')) {
      return null;
    }
    
    if (finalUrl.startsWith('//')) {
      finalUrl = 'https:' + finalUrl;
    } 
    else if (finalUrl.startsWith('/')) {
      if (articleLink) {
        try {
          const urlObj = new URL(articleLink);
          finalUrl = `${urlObj.protocol}//${urlObj.hostname}${finalUrl}`;
        } catch (e) { return null; }
      } else { return null; }
    } 
    else if (!finalUrl.startsWith('http')) {
      if (articleLink) {
        try {
          const urlObj = new URL(articleLink);
          const basePath = articleLink.substring(0, articleLink.lastIndexOf('/') + 1);
          finalUrl = basePath + finalUrl;
        } catch (e) { return null; }
      } else { return null; }
    }

    finalUrl = finalUrl.replace(/&amp;/g, '&');

    const files = fs.readdirSync(IMAGE_DIR);
    const existingFile = files.find(f => f.startsWith(id + '.'));
    if (existingFile) return existingFile;

    let referer = 'https://www.google.com/';
    try {
      const urlObj = new URL(finalUrl);
      referer = `${urlObj.protocol}//${urlObj.hostname}/`;
    } catch (e) {}

    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 15000);

    const response = await fetch(finalUrl, { 
      signal: controller.signal,
      headers: {
        'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1',
        'Accept': 'image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8',
        'Accept-Language': 'fr-FR,fr;q=0.9,en-US;q=0.8,en;q=0.7',
        'Referer': referer,
        'Connection': 'keep-alive'
      }
    });
    
    clearTimeout(timeout);

    if (!response.ok) {
      if (response.status !== 404) {
        console.error(`  [!] Erreur ${response.status} pour ${finalUrl}`);
      }
      return null;
    }

    const contentType = response.headers.get('content-type');
    const ext = await getExtensionFromContentType(contentType);
    const filename = `${id}.${ext}`;
    const filePath = path.join(IMAGE_DIR, filename);

    const arrayBuffer = await response.arrayBuffer();
    const buffer = Buffer.from(arrayBuffer);
    
    if (buffer.length < 500) {
      console.warn(`  [?] Image suspecte (trop petite : ${buffer.length} octets) pour ${finalUrl}`);
      return null;
    }

    await fs.promises.writeFile(filePath, buffer);
    return filename;
  } catch (error: any) {
    if (error.name === 'AbortError') {
      console.error(`  [!] Timeout pour ${url}`);
    } else {
      console.error(`  [!] Erreur :`, error.message);
    }
    return null;
  }
}

async function main() {
  if (!convex.useConvex()) {
    console.error('ERREUR : scripts images portés sur Convex (Phase 4) — définir CONVEX_DEPLOY_KEY et NEXT_PUBLIC_CONVEX_URL.');
    process.exit(1);
  }

  console.log('--- Démarrage du téléchargement des images (Convex) ---');
  
  const articles = await convex.getImagesToDownload();
  console.log(`Articles à traiter : ${articles.length}`);

  let success = 0;
  let failed = 0;

  const BATCH_SIZE = 5;
  for (let i = 0; i < articles.length; i += BATCH_SIZE) {
    const batch = articles.slice(i, i + BATCH_SIZE);
    
    await Promise.all(batch.map(async (article) => {
      try {
        const filename = await downloadImage(article.imageUrl, article.supabaseId ?? article.id, article.link);
        if (filename) {
          await convex.updateArticleLocalImage(article.id, filename);
          success++;
        } else {
          failed++;
        }
      } catch (updateError) {
        failed++;
      }
    }));

    const totalProcessed = i + batch.length;
    if (totalProcessed % 25 === 0 || totalProcessed === articles.length) {
      console.log(`Progression : ${totalProcessed}/${articles.length} (${((totalProcessed/articles.length)*100).toFixed(1)}%)`);
    }
  }

  await downloadArticleImages();

  console.log('\n--- Résumé ---');
  console.log(`Réussis (article) : ${success}`);
  console.log(`Échecs (article)  : ${failed}`);
}

async function downloadArticleImages() {
  console.log('\n--- Téléchargement des images de galerie (ArticleImage) ---');
  const images = await convex.getArticleImagesToDownload();
  console.log(`Images à traiter : ${images.length}`);

  let ok = 0;
  let ko = 0;
  for (const img of images) {
    const filename = await downloadImage(img.url, `gal-${img.id}`, img.articleLink);
    if (filename) {
      await convex.updateArticleImageLocalImage(img.id, filename);
      ok++;
    } else {
      ko++;
    }
  }
  console.log(`Galerie : ${ok} OK, ${ko} échecs`);
}

main()
  .catch((e) => console.error(e));
