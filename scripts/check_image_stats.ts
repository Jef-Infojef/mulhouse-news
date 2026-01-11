import { PrismaClient } from '@prisma/client';

const prisma = new PrismaClient();

async function main() {
  const totalArticles = await prisma.article.count();
  const withImage = await prisma.article.count({
    where: {
      imageUrl: { not: null, notIn: [''] }
    }
  });

  const globalPercentage = (withImage / totalArticles) * 100;

  console.log('--- Rapport sur les Images d\'illustration ---');
  console.log(`Total articles : ${totalArticles}`);
  console.log(`Avec image     : ${withImage}`);
  console.log(`Pourcentage    : ${globalPercentage.toFixed(2)}%\n`);

  // Détail par mois
  const stats: any = await prisma.$queryRaw`
    SELECT 
      TO_CHAR("publishedAt", 'YYYY-MM') as month,
      COUNT(*) as total,
      SUM(CASE WHEN "imageUrl" IS NOT NULL AND "imageUrl" <> '' THEN 1 ELSE 0 END) as has_image
    FROM "Article"
    GROUP BY month
    ORDER BY month DESC;
  `;

  console.log('Détail par mois :');
  stats.forEach((row: any) => {
    const total = Number(row.total);
    const hasImage = Number(row.has_image);
    const pct = (hasImage / total) * 100;
    console.log(`- ${row.month} : ${pct.toFixed(1)}% (${hasImage}/${total})`);
  });
}

main()
  .catch((e) => console.error(e))
  .finally(async () => await prisma.$disconnect());
