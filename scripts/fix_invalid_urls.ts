import { PrismaClient } from '@prisma/client';
import { JSDOM } from 'jsdom';

const prisma = new PrismaClient();

async function findRealImageUrl(articleUrl: string): Promise<string | null> {
  try {
    const res = await fetch(articleUrl, {
      headers: {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36'
      }
    });
    
    if (!res.ok) return null;
    
    const html = await res.text();
    const dom = new JSDOM(html);
    const doc = dom.window.document;

    // On cherche dans les meta tags (priorité og:image)
    const ogImage = doc.querySelector('meta[property="og:image"]')?.getAttribute('content');
    if (ogImage && ogImage.startsWith('http')) return ogImage;

    const twitterImage = doc.querySelector('meta[name="twitter:image"]')?.getAttribute('content');
    if (twitterImage && twitterImage.startsWith('http')) return twitterImage;

    const schemaImage = doc.querySelector('link[rel="image_src"]')?.getAttribute('href');
    if (schemaImage && schemaImage.startsWith('http')) return schemaImage;

    return null;
  } catch (e) {
    return null;
  }
}

async function main() {
  console.log('--- Réparation des URLs d\'images invalides ---');

  const articles = await prisma.article.findMany({
    where: {
      OR: [
        { imageUrl: 'image.png' },
        { imageUrl: { startsWith: '/' } },
        { imageUrl: { endsWith: 'placeholder.jpg' } }
      ]
    },
    take: 50 // On commence par un petit lot
  });

  console.log(`Articles à analyser : ${articles.length}`);

  let fixed = 0;
  for (const article of articles) {
    process.stdout.write(`Analyse : ${article.title.substring(0, 40)}... `);
    const realUrl = await findRealImageUrl(article.link);

    if (realUrl && realUrl !== article.imageUrl) {
      await prisma.article.update({
        where: { id: article.id },
        data: { imageUrl: realUrl }
      });
      console.log('✅ Trouvé !');
      fixed++;
    } else {
      console.log('❌');
    }
  }

  console.log(`\nTerminé ! ${fixed} URLs mises à jour.`);
}

main().catch(console.error).finally(() => prisma.$disconnect());
