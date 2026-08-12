import { PrismaClient } from '@prisma/client';

const prisma = new PrismaClient();

async function main() {
  const start = new Date('2010-01-01');
  const end = new Date(); // Aujourd'hui
  
  // 1. Calcul du nombre total de jours dans la période
  const totalDays = Math.ceil((end.getTime() - start.getTime()) / (1000 * 60 * 60 * 24));

  // 2. Nombre de jours uniques présents en base
  const presentDays: any = await prisma.$queryRaw`
    SELECT COUNT(DISTINCT TO_CHAR("publishedAt", 'YYYY-MM-DD')) as count
    FROM "Article"
    WHERE "publishedAt" >= ${start} AND "publishedAt" <= ${end};
  `;

  const count = Number(presentDays[0].count);
  const globalPct = (count / totalDays) * 100;

  console.log('--- Estimation du Taux de Remplissage (2010-2026) ---');
  console.log(`Période analysée   : 16 ans (${totalDays} jours)`);
  console.log(`Jours couverts     : ${count} jours`);
  console.log(`Taux global        : ${globalPct.toFixed(2)}%\n`);

  // 3. Détail par année pour voir l'évolution
  const yearlyStats: any = await prisma.$queryRaw`
    SELECT 
      EXTRACT(YEAR FROM "publishedAt") as year,
      COUNT(DISTINCT TO_CHAR("publishedAt", 'YYYY-MM-DD')) as days
    FROM "Article"
    WHERE "publishedAt" >= '2010-01-01'
    GROUP BY year
    ORDER BY year DESC;
  `;

  console.log('Couverture par année :');
  yearlyStats.forEach((row: any) => {
    const year = Number(row.year);
    const days = Number(row.days);
    const totalYearDays = (year % 4 === 0 && (year % 100 !== 0 || year % 400 === 0)) ? 366 : 365;
    const pct = (days / (year === 2026 ? 11 : totalYearDays)) * 100; // 2026 n'a que 11 jours
    console.log(`- ${year} : ${pct.toFixed(1)}% (${days} jrs)`);
  });
}

main()
  .catch(console.error)
  .finally(() => prisma.$disconnect());
