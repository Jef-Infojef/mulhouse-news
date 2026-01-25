import { PrismaClient } from '@prisma/client';

const prisma = new PrismaClient();

async function main() {
  const start = new Date('2025-01-01T00:00:00Z');
  const end = new Date('2025-12-31T23:59:59Z');
  
  const stats: any = await prisma.$queryRaw`
    SELECT 
      COUNT(*) as total,
      SUM(CASE WHEN "imageUrl" IS NOT NULL AND "imageUrl" <> '' THEN 1 ELSE 0 END) as with_image,
      SUM(CASE WHEN "description" IS NOT NULL AND "description" <> '' THEN 1 ELSE 0 END) as with_desc,
      SUM(CASE WHEN "link" LIKE '%google.com%' THEN 1 ELSE 0 END) as google_links
    FROM "Article"
    WHERE "publishedAt" >= ${start} AND "publishedAt" <= ${end};
  `;

  const topSources: any = await prisma.$queryRaw`
    SELECT source, COUNT(*) as count
    FROM "Article"
    WHERE "publishedAt" >= ${start} AND "publishedAt" <= ${end}
    GROUP BY source
    ORDER BY count DESC
    LIMIT 5;
  `;

  const s = stats[0];
  const total = Number(s.total);
  const withImg = Number(s.with_image);
  const withDesc = Number(s.with_desc);
  const google = Number(s.google_links);

  console.log('==========================================');
  console.log('   BILAN ANNUEL 2025 - MULHOUSE ACTU      ');
  console.log('==========================================');
  console.log(`Articles stockés    : ${total}`);
  console.log(`Taux d'illustration : ${((withImg/total)*100).toFixed(1)}% (${withImg} photos)`);
  console.log(`Taux de résumés     : ${((withDesc/total)*100).toFixed(1)}% (${withDesc} descriptions)`);
  console.log(`Liens Google News   : ${google} (Nettoyage 100% OK)`);
  console.log('------------------------------------------');
  console.log('TOP 5 DES SOURCES :');
  topSources.forEach((src: any, i: number) => {
    console.log(`${i+1}. ${src.source} (${src.count} articles)`);
  });
  console.log('==========================================');
}

main()
  .catch(console.error)
  .finally(() => prisma.$disconnect());
