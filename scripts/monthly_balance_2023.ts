import { PrismaClient } from '@prisma/client';

const prisma = new PrismaClient({
  datasources: {
    db: {
      url: "process.env.DATABASE_URL || """
    },
  },
});

async function main() {
  const stats: any = await prisma.$queryRaw`
    SELECT 
      TO_CHAR("publishedAt", 'YYYY-MM') as month,
      COUNT(*) as total,
      SUM(CASE WHEN "imageUrl" IS NOT NULL AND "imageUrl" <> '' THEN 1 ELSE 0 END) as with_image,
      SUM(CASE WHEN "description" IS NOT NULL AND "description" <> '' THEN 1 ELSE 0 END) as with_desc
    FROM "Article"
    WHERE "publishedAt" >= '2023-01-01' AND "publishedAt" <= '2023-12-31'
    GROUP BY month
    ORDER BY month ASC;
  `;

  console.log('--- Bilan Mensuel 2023 ---');
  if (stats.length === 0) {
    console.log('Aucun article trouvé pour l\'année 2023.');
  } else {
    console.log('┌─────────┬────────┬────────┬────────┬────────┐');
    console.log('│ Mois    │ Total  │ Photos │ % Img  │ Descr. │');
    console.log('├─────────┼────────┼────────┼────────┼────────┤');

    let totalYear = 0;
    stats.forEach((row: any) => {
      const total = Number(row.total);
      const img = Number(row.with_image);
      const desc = Number(row.with_desc);
      const pctImg = total > 0 ? (img / total) * 100 : 0;
      totalYear += total;
      
      console.log(`│ ${row.month} │ ${total.toString().padEnd(6)} │ ${img.toString().padEnd(6)} │ ${pctImg.toFixed(1).padEnd(5)}% │ ${desc.toString().padEnd(6)} │`);
    });
    console.log('├─────────┼────────┼────────┼────────┼────────┤');
    console.log(`│ TOTAL   │ ${totalYear.toString().padEnd(6)} │        │        │        │`);
    console.log('└─────────┴────────┴────────┴────────┴────────┘');
  }
}

main()
  .catch((e) => console.error(e))
  .finally(async () => await prisma.$disconnect());
