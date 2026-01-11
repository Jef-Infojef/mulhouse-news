import { PrismaClient } from '@prisma/client';

const prisma = new PrismaClient();

async function generateReport(monthName: string, startStr: string, endStr: string) {
  const start = new Date(startStr);
  const end = new Date(endStr);

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

  console.log(`\n--- Rapport ${monthName} (${articles.length} articles) ---`);
  
  const sourceStats: Record<string, number> = {};
  articles.forEach(a => {
    const src = a.source || 'Inconnu';
    sourceStats[src] = (sourceStats[src] || 0) + 1;
  });

  console.log('Répartition par source :');
  Object.entries(sourceStats)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 10)
    .forEach(([src, count]) => console.log(`- ${src}: ${count}`));

  console.log('\nÉchantillon des premiers articles :');
  articles.slice(0, 5).forEach((a, i) => {
    console.log(`${i + 1}. [${a.publishedAt.toISOString().split('T')[0]}] [${a.source}] ${a.title}`);
  });
}

async function main() {
  await generateReport('Mars 2025', '2025-03-01T00:00:00Z', '2025-03-31T23:59:59Z');
  await generateReport('Mai 2025', '2025-05-01T00:00:00Z', '2025-05-31T23:59:59Z');
}

main()
  .catch((e) => console.error(e))
  .finally(async () => await prisma.$disconnect());
