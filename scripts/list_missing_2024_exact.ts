import { PrismaClient } from '@prisma/client';

const prisma = new PrismaClient();

async function main() {
  console.log('--- Liste Précise des Jours Manquants en 2024 ---');
  
  const stats: any = await prisma.$queryRaw`
    SELECT 
      TO_CHAR("publishedAt", 'YYYY-MM-DD') as date
    FROM "Article"
    WHERE "publishedAt" >= '2024-01-01' AND "publishedAt" <= '2024-12-31'
    GROUP BY date;
  `;

  const presentDates = new Set(stats.map((s: any) => s.date));
  const missingDates: string[] = [];

  const startDate = new Date('2024-01-01');
  const endDate = new Date('2024-12-31');
  let currentDate = new Date(startDate);

  while (currentDate <= endDate) {
    const dateStr = currentDate.toISOString().split('T')[0];
    if (!presentDates.has(dateStr)) {
      missingDates.push(dateStr);
    }
    currentDate.setDate(currentDate.getDate() + 1);
  }

  if (missingDates.length === 0) {
    console.log('✅ L\'année 2024 est complète !');
  } else {
    // Grouper par mois pour la lisibilité
    const grouped: Record<string, string[]> = {};
    missingDates.forEach(d => {
      const month = d.substring(0, 7);
      if (!grouped[month]) grouped[month] = [];
      grouped[month].push(d);
    });

    for (const [month, days] of Object.entries(grouped)) {
      console.log(`
${month} (${days.length} jours) :`);
      console.log(`   ${days.join(', ')}`);
    }
  }
}

main()
  .catch(console.error)
  .finally(() => prisma.$disconnect());
