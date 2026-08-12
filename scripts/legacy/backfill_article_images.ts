import { PrismaClient } from '@prisma/client';
import * as dotenv from 'dotenv';

dotenv.config();
dotenv.config({ path: '.env.local' });

const prisma = new PrismaClient();

async function main() {
  const articles = await prisma.article.findMany({
    where: {
      imageUrl: { not: null, notIn: ['', 'null'] }
    },
    select: {
      id: true,
      imageUrl: true,
      imageCaption: true
    }
  });

  const existing = await prisma.articleImage.findMany({
    where: { source: 'hero' },
    select: { articleId: true, url: true }
  });

  const existingHero = new Set(existing.map(e => `${e.articleId}::${e.url}`));

  let created = 0;
  for (const article of articles) {
    if (existingHero.has(`${article.id}::${article.imageUrl}`)) continue;

    try {
      await prisma.articleImage.create({
        data: {
          articleId: article.id,
          url: article.imageUrl!,
          caption: article.imageCaption,
          position: 0,
          source: 'hero'
        }
      });
      created++;
    } catch (e) {
      console.error(`Erreur pour ${article.id}:`, e);
    }
  }

  console.log(`Articles traités : ${articles.length}`);
  console.log(`ArticleImage créés : ${created}`);
}

main()
  .catch(console.error)
  .finally(() => prisma.$disconnect());