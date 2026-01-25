import { PrismaClient } from '@prisma/client';

const prisma = new PrismaClient();

async function main() {
  console.log('--- Recherche des Jours Manquants en 2025 ---');
  
  const stats: any = await prisma.$queryRaw`
    SELECT 
      TO_CHAR("publishedAt", 'YYYY-MM-DD') as date,
      COUNT(*) as count
    FROM "Article"
    WHERE "publishedAt" >= '2025-01-01' AND "publishedAt" <= '2025-12-31'
    GROUP BY date
    ORDER BY date ASC;
  `;

  const presentDates = new Set(stats.map((s: any) => s.date));
  const missingByMonth: Record<string, string[]> = {};

  const startDate = new Date('2025-01-01');
  const endDate = new Date('2025-12-31');
  let currentDate = new Date(startDate);

  while (currentDate <= endDate) {
    const dateStr = currentDate.toISOString().split('T')[0];
    if (!presentDates.has(dateStr)) {
      const month = dateStr.substring(0, 7);
      if (!missingByMonth[month]) missingByMonth[month] = [];
      missingByMonth[month].push(dateStr);
    }
    currentDate.setDate(currentDate.getDate() + 1);
  }

  const months = Object.keys(missingByMonth).sort();
  if (months.length === 0) {
    console.log('✅ Aucun jour manquant trouvé en 2025 !');
  } else {
    months.forEach(month => {
      console.log(`
${month} : ${missingByMonth[month].length} jours manquants`);
      console.log(`   -> ${missingByMonth[month].join(', ')}`);
    });
  }
}

main()
  .catch(console.error)
  .finally(() => prisma.$disconnect());
