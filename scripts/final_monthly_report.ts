import { PrismaClient } from '@prisma/client';

const prisma = new PrismaClient();

async function main() {
  const stats: any = await prisma.$queryRaw`
    SELECT 
      TO_CHAR("publishedAt", 'YYYY-MM') as month,
      COUNT(*) as total,
      SUM(CASE WHEN "imageUrl" IS NOT NULL AND "imageUrl" <> '' THEN 1 ELSE 0 END) as has_image
    FROM "Article"
    GROUP BY month
    ORDER BY month DESC;
  `;

  console.log('--- Rapport Mensuel Actualisé (Sans liens Google) ---');
  console.log('┌─────────┬────────┬────────┬────────┐');
  console.log('│ Mois    │ Total  │ Photos │ % Img  │');
  console.log('├─────────┼────────┼────────┼────────┤');

  stats.forEach((row: any) => {
    const total = Number(row.total);
    const hasImage = Number(row.has_image);
    const pct = (hasImage / total) * 100;
    console.log(`│ ${row.month} │ ${total.toString().padEnd(6)} │ ${hasImage.toString().padEnd(6)} │ ${pct.toFixed(1).padEnd(5)}% │`);
  });
  console.log('└─────────┴────────┴────────┴────────┘');
}

main()
  .catch((e) => console.error(e))
  .finally(async () => await prisma.$disconnect());
