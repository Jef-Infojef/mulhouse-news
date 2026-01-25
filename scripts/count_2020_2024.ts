import { PrismaClient } from '@prisma/client';

const prisma = new PrismaClient();

async function main() {
  console.log('--- Décompte des articles par année (2020-2024) ---');
  
  const stats: any = await prisma.$queryRaw`
    SELECT 
      EXTRACT(YEAR FROM "publishedAt") as year,
      COUNT(*) as total
    FROM "Article"
    WHERE "publishedAt" >= '2020-01-01' AND "publishedAt" <= '2024-12-31'
    GROUP BY year
    ORDER BY year ASC;
  `;

  if (stats.length === 0) {
    console.log('Aucun article trouvé dans cette période.');
  } else {
    console.table(stats.map((row: any) => ({
      Année: Number(row.year),
      Articles: Number(row.total)
    })));
  }
}

main()
  .catch((e) => console.error(e))
  .finally(async () => await prisma.$disconnect());
