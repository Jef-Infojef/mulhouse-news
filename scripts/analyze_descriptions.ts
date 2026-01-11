import { PrismaClient } from '@prisma/client';

const prisma = new PrismaClient();

async function main() {
  const articles = await prisma.article.findMany({
    where: {
      publishedAt: {
        gte: new Date('2026-01-01T00:00:00Z'),
      },
      description: { not: null, notIn: [''] }
    },
    select: {
      description: true
    }
  });

  if (articles.length === 0) {
    console.log('Aucun article avec description trouvé en Janvier 2026.');
    return;
  }

  let totalLength = 0;
  let atLimit = 0;
  const limit = 247; // Car j'ajoute "..." après 247

  articles.forEach(a => {
    const len = a.description?.length || 0;
    totalLength += len;
    if (len >= limit) atLimit++;
  });

  console.log(`--- Analyse Descriptions Janvier 2026 ---`);
  console.log(`Nombre d'articles analysés : ${articles.length}`);
  console.log(`Longueur moyenne : ${Math.round(totalLength / articles.length)} caractères`);
  console.log(`Articles à la limite (${limit}+) : ${atLimit} (${((atLimit/articles.length)*100).toFixed(1)}%)`);
}

main()
  .catch((e) => console.error(e))
  .finally(async () => await prisma.$disconnect());
