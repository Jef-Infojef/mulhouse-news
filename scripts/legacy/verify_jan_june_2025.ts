import { PrismaClient } from '@prisma/client';

const prisma = new PrismaClient();

async function main() {
  const start = new Date('2025-01-01T00:00:00Z');
  const end = new Date('2025-06-30T23:59:59Z');
  
  const stats: any = await prisma.$queryRaw`
    SELECT 
      TO_CHAR("publishedAt", 'YYYY-MM') as month,
      COUNT(*) as total,
      SUM(CASE WHEN "imageUrl" IS NOT NULL AND "imageUrl" <> '' THEN 1 ELSE 0 END) as with_image,
      SUM(CASE WHEN "description" IS NOT NULL AND "description" <> '' THEN 1 ELSE 0 END) as with_desc,
      AVG(CASE WHEN "description" IS NOT NULL AND "description" <> '' THEN LENGTH("description") ELSE NULL END) as avg_desc_len,
      SUM(CASE WHEN "link" LIKE '%google.com%' THEN 1 ELSE 0 END) as google_links
    FROM "Article"
    WHERE "publishedAt" >= ${start} AND "publishedAt" <= ${end}
    GROUP BY month
    ORDER BY month ASC;
  `;

  console.log('--- Rapport Qualité : 1er Semestre 2025 ---');
  console.log('┌─────────┬────────┬────────┬────────┬────────┬────────┐');
  console.log('│ Mois    │ Total  │ Photos │ % Img  │ Descr. │ Google │');
  console.log('├─────────┼────────┼────────┼────────┼────────┼────────┤');

  let totalArts = 0;
  let totalImg = 0;
  let totalDesc = 0;
  let totalGoogle = 0;

  stats.forEach((row: any) => {
    const total = Number(row.total);
    const img = Number(row.with_image);
    const desc = Number(row.with_desc);
    const google = Number(row.google_links);
    const pctImg = (img / total) * 100;
    
    totalArts += total;
    totalImg += img;
    totalDesc += desc;
    totalGoogle += google;

    console.log(`│ ${row.month} │ ${total.toString().padEnd(6)} │ ${img.toString().padEnd(6)} │ ${pctImg.toFixed(1).padEnd(5)}% │ ${desc.toString().padEnd(6)} │ ${google.toString().padEnd(6)} │`);
  });

  console.log('├─────────┼────────┼────────┼────────┼────────┼────────┤');
  const totalPctImg = totalArts > 0 ? (totalImg / totalArts) * 100 : 0;
  console.log(`│ TOTAL   │ ${totalArts.toString().padEnd(6)} │ ${totalImg.toString().padEnd(6)} │ ${totalPctImg.toFixed(1).padEnd(5)}% │ ${totalDesc.toString().padEnd(6)} │ ${totalGoogle.toString().padEnd(6)} │`);
  console.log('└─────────┴────────┴────────┴────────┴────────┴────────┘');
}

main()
  .catch(console.error)
  .finally(() => prisma.$disconnect());
