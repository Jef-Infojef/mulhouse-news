import { PrismaClient } from '@prisma/client';

const prisma = new PrismaClient();

async function main() {
  console.log('--- Recherche des Jours Manquants en 2024 ---');
  
  const stats: any = await prisma.$queryRaw`
    SELECT 
      TO_CHAR("publishedAt", 'YYYY-MM-DD') as date
    FROM "Article"
    WHERE "publishedAt" >= '2024-01-01' AND "publishedAt" <= '2024-12-31'
    GROUP BY date;
  `;

  const presentDates = new Set(stats.map((s: any) => s.date));
  const missingByMonth: Record<string, number> = {};

  const startDate = new Date('2024-01-01');
  const endDate = new Date('2024-12-31');
  let currentDate = new Date(startDate);

  while (currentDate <= endDate) {
    const dateStr = currentDate.toISOString().split('T')[0];
    if (!presentDates.has(dateStr)) {
      const month = dateStr.substring(0, 7);
      missingByMonth[month] = (missingByMonth[month] || 0) + 1;
    }
    currentDate.setDate(currentDate.getDate() + 1);
  }

  const months = [
    '2024-01', '2024-02', '2024-03', '2024-04', '2024-05', '2024-06',
    '2024-07', '2024-08', '2024-09', '2024-10', '2024-11', '2024-12'
  ];

  console.log('État de couverture par mois :');
  months.forEach(m => {
    const missing = missingByMonth[m] || 0;
    const daysInMonth = new Date(Number(m.split('-')[0]), Number(m.split('-')[1]), 0).getDate();
    const present = daysInMonth - missing;
    const status = missing === 0 ? "✅ COMPLET" : (present === 0 ? "❌ VIDE" : `⚠️ ${present}/${daysInMonth} jours`);
    console.log(`${m} : ${status}`);
  });
}

main()
  .catch(console.error)
  .finally(() => prisma.$disconnect());
