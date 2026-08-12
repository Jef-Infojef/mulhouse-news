import { PrismaClient } from '@prisma/client';

const prisma = new PrismaClient();

async function main() {
  console.log('--- Rapport Annuel 2025 ---');
  
  const stats: any = await prisma.$queryRaw`
    SELECT 
      TO_CHAR("publishedAt", 'YYYY-MM') as month,
      COUNT(*) as total,
      SUM(CASE WHEN "link" LIKE '%google.com%' THEN 1 ELSE 0 END) as google_links,
      SUM(CASE WHEN "imageUrl" IS NOT NULL AND "imageUrl" <> '' THEN 1 ELSE 0 END) as with_image
    FROM "Article"
    WHERE "publishedAt" >= '2025-01-01' AND "publishedAt" <= '2025-12-31'
    GROUP BY month
    ORDER BY month ASC;
  `;

  let yearTotal = 0;
  let yearWithImage = 0;
  let yearGoogle = 0;

  console.log('┌─────────┬────────┬────────┬────────┬────────┐');
  console.log('│ Mois    │ Total  │ Image  │ % Img  │ Google │');
  console.log('├─────────┼────────┼────────┼────────┼────────┤');

  stats.forEach((row: any) => {
    const total = Number(row.total);
    const hasImage = Number(row.with_image);
    const google = Number(row.google_links);
    const pct = (hasImage / total) * 100;
    
    yearTotal += total;
    yearWithImage += hasImage;
    yearGoogle += google;

    console.log(`│ ${row.month} │ ${total.toString().padEnd(6)} │ ${hasImage.toString().padEnd(6)} │ ${pct.toFixed(1).padEnd(5)}% │ ${google.toString().padEnd(6)} │`);
  });

  console.log('├─────────┼────────┼────────┼────────┼────────┤');
  const yearPct = yearTotal > 0 ? (yearWithImage / yearTotal) * 100 : 0;
  console.log(`│ TOTAL   │ ${yearTotal.toString().padEnd(6)} │ ${yearWithImage.toString().padEnd(6)} │ ${yearPct.toFixed(1).padEnd(5)}% │ ${yearGoogle.toString().padEnd(6)} │`);
  console.log('└─────────┴────────┴────────┴────────┴────────┘');

  // Top sources de l'année
  const topSources = await prisma.article.groupBy({
    by: ['source'],
    where: { publishedAt: { gte: new Date('2025-01-01'), lte: new Date('2025-12-31') } },
    _count: { id: true },
    orderBy: { _count: { id: 'desc' } },
    take: 5
  });

  console.log('\nTop 5 Sources 2025 :');
  topSources.forEach(s => {
    const count = s._count?.id ?? 0;
    console.log(`- ${s.source}: ${count} articles`);
  });
}

main()
  .catch((e) => console.error(e))
  .finally(async () => await prisma.$disconnect());
