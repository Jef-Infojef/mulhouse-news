import { PrismaClient } from '@prisma/client';

const prisma = new PrismaClient();

async function main() {
  const missingImages = await prisma.article.groupBy({
    by: ['source'],
    where: {
      OR: [
        { imageUrl: null },
        { imageUrl: '' }
      ]
    },
    _count: {
      id: true
    },
    orderBy: {
      _count: {
        id: 'desc'
      }
    },
    take: 20
  });

  console.log('--- Top 20 des sources sans photos ---');
  missingImages.forEach((item: any) => {
    console.log(`${item.source || 'Inconnu'}: ${item._count.id} articles sans photo`);
  });
}

main()
  .catch((e) => console.error(e))
  .finally(async () => await prisma.$disconnect());