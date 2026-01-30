import { PrismaClient } from '@prisma/client';

const prisma = new PrismaClient();

async function main() {
  const stats: any = await prisma.$queryRaw`
    SELECT 
      TO_CHAR("publishedAt", 'YYYY-MM') as month,
      COUNT(*) as total,
      SUM(CASE WHEN "imageUrl" IS NOT NULL AND "imageUrl" <> '' THEN 1 ELSE 0 END) as with_image,
      SUM(CASE WHEN "description" IS NOT NULL AND "description" <> '' THEN 1 ELSE 0 END) as with_desc
    FROM "Article"
    WHERE "publishedAt" >= '2025-01-01' AND "publishedAt" <= '2025-12-31'
    GROUP BY month
    ORDER BY month ASC;
  `;

  console.log('--- Bilan Mensuel 2025 ---');
  console.log('┌─────────┬────────┬────────┬────────┬────────┐');
  console.log('│ Mois    │ Total  │ Photos │ % Img  │ Descr. │');
  console.log('├─────────┼────────┼────────┼────────┼────────┤');

  stats.forEach((row: any) => {
    const total = Number(row.total);
    const img = Number(row.with_image);
    const desc = Number(row.with_desc);
    const pctImg = (img / total) * 100;
    
    console.log(`│ ${row.month} │ ${total.toString().padEnd(6)} │ ${img.toString().padEnd(6)} │ ${pctImg.toFixed(1).padEnd(5)}% │ ${desc.toString().padEnd(6)} │`);
  });
  console.log('└─────────┴────────┴────────┴────────┴────────┘');
}

main()
  .catch(console.error)
  .finally(() => prisma.$disconnect());
