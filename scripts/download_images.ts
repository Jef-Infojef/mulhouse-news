import { PrismaClient } from '@prisma/client';
import fs from 'fs';
import path from 'path';

const prisma = new PrismaClient();
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
  console.log('--- Démarrage du téléchargement des images ---');
  
  const articles = await prisma.article.findMany({
    where: {
      imageUrl: { not: null, notIn: ['', 'null'] },
      localImage: null
    },
    select: {
      id: true,
      imageUrl: true,
      link: true
    },
    orderBy: {
      publishedAt: 'desc'
    }
  });

  console.log(`Articles à traiter : ${articles.length}`);
  if (articles.length === 0) {
    console.log('Tout est déjà à jour !');
    return;
  }

  let success = 0;
  let failed = 0;

  const BATCH_SIZE = 5;
  for (let i = 0; i < articles.length; i += BATCH_SIZE) {
    const batch = articles.slice(i, i + BATCH_SIZE);
    
    await Promise.all(batch.map(async (article) => {
      try {
        const filename = await downloadImage(article.imageUrl!, article.id, article.link);
        if (filename) {
          await prisma.article.update({
            where: { id: article.id },
            data: { localImage: filename }
          });
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

  console.log('\n--- Résumé ---');
  console.log(`Réussis   : ${success}`);
  console.log(`Échecs    : ${failed}`);
}

main()
  .catch((e) => console.error(e))
  .finally(async () => await prisma.$disconnect());