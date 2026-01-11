import { PrismaClient } from '@prisma/client';

const prisma = new PrismaClient();

async function checkMonth(name: string, startStr: string, endStr: string) {
  const start = new Date(startStr);
  const end = new Date(endStr);

  const total = await prisma.article.count({
    where: { publishedAt: { gte: start, lte: end } }
  });

  const withImage = await prisma.article.count({
    where: { 
      publishedAt: { gte: start, lte: end },
      imageUrl: { not: null, notIn: [''] }
    }
  });

  const pct = total > 0 ? (withImage / total) * 100 : 0;
  console.log(`${name} : ${pct.toFixed(1)}% (${withImage}/${total})`);
}

async function main() {
  console.log('--- Rapport Complémentaire 2025 ---');
  await checkMonth('Juin 2025  ', '2025-06-01T00:00:00Z', '2025-06-30T23:59:59Z');
  await checkMonth('Juillet 2025', '2025-07-01T00:00:00Z', '2025-07-31T23:59:59Z');
  await checkMonth('Août 2025   ', '2025-08-01T00:00:00Z', '2025-08-31T23:59:59Z');
  await checkMonth('Septembre 2025', '2025-09-01T00:00:00Z', '2025-09-30T23:59:59Z');
}

main()
  .catch((e) => console.error(e))
  .finally(async () => await prisma.$disconnect());
