import { PrismaClient } from '@prisma/client';

const prisma = new PrismaClient();

async function main() {
  const missingDesc = await prisma.article.groupBy({
    by: ['source'],
    where: {
      OR: [
        { description: null },
        { description: '' }
      ]
    },
    _count: { id: true },
    orderBy: { _count: { id: 'desc' } },
    take: 20
  });

  console.log('--- Top 20 des sources sans descriptions ---');
  missingDesc.forEach((item: any) => {
    console.log(`${item.source || 'Inconnu'}: ${item._count.id} articles`);
  });
}

main()
  .catch(console.error)
  .finally(() => prisma.$disconnect());
