import { PrismaClient } from '@prisma/client';

const prisma = new PrismaClient();

async function main() {
  const stats = await prisma.$queryRaw`
    SELECT 
      TO_CHAR("publishedAt", 'YYYY-MM') as month,
      COUNT(*) as count
    FROM "Article"
    GROUP BY month
    ORDER BY month DESC;
  `;

  console.log('--- Rapport des articles par mois ---');
  console.table(stats);
}

main()
  .catch((e) => console.error(e))
  .finally(async () => await prisma.$disconnect());
