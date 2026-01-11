import { PrismaClient } from '@prisma/client';

const prisma = new PrismaClient();

async function main() {
  const start = new Date('2025-07-01T00:00:00Z');
  const end = new Date('2025-07-31T23:59:59Z');

  const total = await prisma.article.count({
    where: { publishedAt: { gte: start, lte: end } }
  });

  const googleLinks = await prisma.article.count({
    where: { 
      publishedAt: { gte: start, lte: end },
      link: { contains: 'google.com' }
    }
  });

  const withImage = await prisma.article.count({
    where: { 
      publishedAt: { gte: start, lte: end },
      imageUrl: { not: null, notIn: [''] }
    }
  });

  console.log(`--- Rapport Juillet 2025 ---`);
  console.log(`Total articles : ${total}`);
  console.log(`Liens Google   : ${googleLinks}`);
  console.log(`Avec photo     : ${withImage}`);
  
  if (total > 0) {
    console.log(`Taux de photos : ${((withImage / total) * 100).toFixed(1)}%`);
  }
}

main()
  .catch((e) => console.error(e))
  .finally(async () => await prisma.$disconnect());
