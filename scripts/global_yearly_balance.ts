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
      EXTRACT(YEAR FROM "publishedAt") as year,
      COUNT(*) as total,
      SUM(CASE WHEN "imageUrl" IS NOT NULL AND "imageUrl" <> '' THEN 1 ELSE 0 END) as with_image,
      SUM(CASE WHEN "description" IS NOT NULL AND "description" <> '' THEN 1 ELSE 0 END) as with_desc
    FROM "Article"
    GROUP BY year
    ORDER BY year ASC;
  `;

  console.log('====================================================');
  console.log('       BILAN GLOBAL PAR ANNÉE - MULHOUSE ACTU       ');
  console.log('====================================================');
  console.log('┌──────┬────────┬────────┬────────┬────────┐');
  console.log('│ Année│ Total  │ Photos │ % Img  │ Descr. │');
  console.log('├──────┼────────┼────────┼────────┼────────┤');

  let grandTotal = 0;
  let grandPhotos = 0;
  let grandDesc = 0;

  stats.forEach((row: any) => {
    const year = Math.floor(Number(row.year));
    const total = Number(row.total);
    const img = Number(row.with_image);
    const desc = Number(row.with_desc);
    const pctImg = (img / total) * 100;
    
    grandTotal += total;
    grandPhotos += img;
    grandDesc += desc;

    console.log(`│ ${year} │ ${total.toString().padEnd(6)} │ ${img.toString().padEnd(6)} │ ${pctImg.toFixed(1).padEnd(5)}% │ ${desc.toString().padEnd(6)} │`);
  });

  console.log('├──────┼────────┼────────┼────────┼────────┤');
  const grandPctImg = (grandPhotos / grandTotal) * 100;
  console.log(`│ TOTAL│ ${grandTotal.toString().padEnd(6)} │ ${grandPhotos.toString().padEnd(6)} │ ${grandPctImg.toFixed(1).padEnd(5)}% │ ${grandDesc.toString().padEnd(6)} │`);
  console.log('└──────┴────────┴────────┴────────┴────────┘');
  console.log('====================================================');
}

main()
  .catch((e) => console.error(e))
  .finally(async () => await prisma.$disconnect());
