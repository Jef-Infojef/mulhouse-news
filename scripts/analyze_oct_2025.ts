import { PrismaClient } from '@prisma/client';

const prisma = new PrismaClient();

async function main() {
  const start = new Date('2025-10-01T00:00:00Z');
  const end = new Date('2025-10-31T23:59:59Z');
  
  const articles = await prisma.article.findMany({
    where: {
      publishedAt: { gte: start, lte: end }
    },
    select: {
      imageUrl: true,
      description: true,
      source: true
    }
  });

  const total = articles.length;
  if (total === 0) {
    console.log('Aucun article trouvé pour Octobre 2025.');
    return;
  }

  const withPhoto = articles.filter(a => a.imageUrl && a.imageUrl !== '').length;
  const withDesc = articles.filter(a => a.description && a.description !== '').length;
  
  const descLengths = articles
    .filter(a => a.description && a.description !== '')
    .map(a => a.description!.length);
    
  const avgDesc = descLengths.length > 0 
    ? Math.round(descLengths.reduce((a, b) => a + b, 0) / descLengths.length) 
    : 0;
    
  const maxDesc = descLengths.length > 0 ? Math.max(...descLengths) : 0;

  console.log(`--- Analyse Octobre 2025 ---`);
  console.log(`Nombre total d'articles : ${total}`);
  console.log(`Articles avec photo     : ${withPhoto} (${((withPhoto/total)*100).toFixed(1)}%)`);
  console.log(`Articles avec desc.     : ${withDesc} (${((withDesc/total)*100).toFixed(1)}%)`);
  console.log(`Longueur moyenne desc.  : ${avgDesc} caractères`);
  console.log(`Longueur maximale desc. : ${maxDesc} caractères`);
  
  // Détail par source pour les photos
  const sources: any = await prisma.$queryRaw`
    SELECT source, COUNT(*) as total, 
    SUM(CASE WHEN "imageUrl" IS NOT NULL AND "imageUrl" <> '' THEN 1 ELSE 0 END) as has_img
    FROM "Article"
    WHERE "publishedAt" >= '2025-10-01' AND "publishedAt" <= '2025-10-31'
    GROUP BY source
    ORDER BY total DESC
    LIMIT 10;
  `;
  
  console.log('\nTop 10 Sources (Taux de photos) :');
  sources.forEach((s: any) => {
    const totalS = Number(s.total);
    const hasImgS = Number(s.has_img);
    const pct = (hasImgS / totalS) * 100;
    console.log(`- ${s.source}: ${pct.toFixed(1)}% (${hasImgS}/${totalS})`);
  });
}

main()
  .catch(console.error)
  .finally(() => prisma.$disconnect());
