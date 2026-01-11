import { PrismaClient } from '@prisma/client';

const prisma = new PrismaClient();

async function main() {
  const start = new Date('2025-10-01T00:00:00Z');
  const end = new Date('2025-10-01T23:59:59Z');

  const articles = await prisma.article.findMany({
    where: {
      publishedAt: {
        gte: start,
        lte: end,
      },
    },
    select: {
      title: true,
      link: true,
      publishedAt: true,
      source: true,
    },
    orderBy: {
      publishedAt: 'asc',
    },
  });

  console.log(`Nombre d'articles trouvés pour le 2025-10-01 : ${articles.length}`);
  articles.forEach((art, i) => {
    console.log(`${i + 1}. [${art.source}] ${art.title}`);
    console.log(`   Lien : ${art.link}`);
  });
}

main()
  .catch((e) => {
    console.error(e);
    process.exit(1);
  })
  .finally(async () => {
    await prisma.$disconnect();
  });
