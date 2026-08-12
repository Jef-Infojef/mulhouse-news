import { PrismaClient } from '@prisma/client';

const prisma = new PrismaClient();

async function main() {
  const start = new Date('2025-02-01T00:00:00Z');
  const end = new Date('2025-02-28T23:59:59Z');

  const articles = await prisma.article.findMany({
    where: {
      publishedAt: {
        gte: start,
        lte: end,
      },
    },
    select: {
      title: true,
      source: true,
      publishedAt: true,
    },
    orderBy: {
      publishedAt: 'asc',
    },
  });

  console.log(`--- Rapport Février 2025 (${articles.length} articles) ---`);
  
  // Grouper par source pour le résumé
  const sourceStats: Record<string, number> = {};
  articles.forEach(a => {
    const src = a.source || 'Inconnu';
    sourceStats[src] = (sourceStats[src] || 0) + 1;
  });

  console.log('\nRépartition par source :');
  Object.entries(sourceStats)
    .sort((a, b) => b[1] - a[1])
    .forEach(([src, count]) => console.log(`- ${src}: ${count}`));

  console.log('\nÉchantillon des premiers articles du mois :');
  articles.slice(0, 15).forEach((a, i) => {
    console.log(`${i + 1}. [${a.publishedAt.toISOString().split('T')[0]}] [${a.source}] ${a.title}`);
  });
}

main()
  .catch((e) => console.error(e))
  .finally(async () => await prisma.$disconnect());
