import { PrismaClient } from '@prisma/client';

const prisma = new PrismaClient();

async function main() {
  const start = new Date('2025-10-01T00:00:00Z');
  const end = new Date('2025-10-31T23:59:59Z');

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

  console.log(`--- Rapport Octobre 2025 (${articles.length} articles) ---`);
  
  const sourceStats: Record<string, number> = {};
  articles.forEach(a => {
    const src = a.source || 'Inconnu';
    sourceStats[src] = (sourceStats[src] || 0) + 1;
  });

  console.log('\nRépartition par source :');
  Object.entries(sourceStats)
    .sort((a, b) => b[1] - a[1])
    .forEach(([src, count]) => console.log(`- ${src}: ${count}`));

  console.log('\nChronologie (nombre par jour) :');
  const dayStats: Record<string, number> = {};
  articles.forEach(a => {
    const day = a.publishedAt.toISOString().split('T')[0];
    dayStats[day] = (dayStats[day] || 0) + 1;
  });
  Object.entries(dayStats).forEach(([day, count]) => console.log(`- ${day}: ${count}`));

  console.log('\nÉchantillon des articles :');
  articles.slice(0, 10).forEach((a, i) => {
    console.log(`${i + 1}. [${a.publishedAt.toISOString().split('T')[0]}] [${a.source}] ${a.title}`);
  });
}

main()
  .catch((e) => console.error(e))
  .finally(async () => await prisma.$disconnect());
