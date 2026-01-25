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
  if (contentType.includes('image/png')) return 'png';
  if (contentType.includes('image/webp')) return 'webp';
  return 'jpg';
}

async function downloadRosselImage(url: string, id: string): Promise<string | null> {
  try {
    // On utilise l'URL brute sans re-encodage qui pourrait casser le %2B (+)
    const response = await fetch(url, { 
      headers: {
        'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1',
        'Accept': 'image/avif,image/webp,image/apng/image/svg+xml,image/*,*/*;q=0.8',
        'Referer': 'https://www.lalsace.fr/',
        'Cache-Control': 'no-cache'
      }
    });

    if (!response.ok) {
      console.error(`  [!] Échec ${response.status} pour ${id}`);
      return null;
    }

    const contentType = response.headers.get('content-type');
    const ext = await getExtensionFromContentType(contentType);
    const filename = `${id}.${ext}`;
    const filePath = path.join(IMAGE_DIR, filename);

    const arrayBuffer = await response.arrayBuffer();
    const buffer = Buffer.from(arrayBuffer);
    
    if (buffer.length < 1000) return null;

    await fs.promises.writeFile(filePath, buffer);
    return filename;
  } catch (error: any) {
    console.error(`  [!] Erreur ${id}:`, error.message);
    return null;
  }
}

async function main() {
  console.log('--- Focus : Groupe Rossel (L\'Alsace/DNA) ---');
  
  const articles = await prisma.article.findMany({
    where: { 
      imageUrl: { contains: 'rosselcdn.net' },
      localImage: null
    },
    select: { id: true, imageUrl: true, title: true },
    take: 500
  });

  console.log(`Articles à traiter : ${articles.length}`);

  let success = 0;
  for (const article of articles) {
    process.stdout.write(`Traitement : ${article.id}... `);
    const filename = await downloadRosselImage(article.imageUrl!, article.id);
    
    if (filename) {
      await prisma.article.update({
        where: { id: article.id },
        data: { localImage: filename }
      });
      console.log('✅');
      success++;
    } else {
      console.log('❌');
    }
  }

  console.log(`\nTerminé ! ${success} images récupérées.`);
}

main().catch(console.error).finally(() => prisma.$disconnect());
