import { PrismaClient } from '@prisma/client';

const prisma = new PrismaClient();

async function main() {
  const novCount = await prisma.article.count({
    where: {
      publishedAt: {
        gte: new Date('2025-11-01T00:00:00Z'),
        lte: new Date('2025-11-30T23:59:59Z'),
      }
    }
  });

  const decCount = await prisma.article.count({
    where: {
      publishedAt: {
        gte: new Date('2025-12-01T00:00:00Z'),
        lte: new Date('2025-12-31T23:59:59Z'),
      }
    }
  });

  const totalSizeKB = 2600; // Taille actuelle de la table Article
  const totalArticles = 1400;
  const kbPerArticle = totalSizeKB / totalArticles;

  console.log(`Articles en Novembre : ${novCount}`);
  console.log(`Articles en Décembre : ${decCount}`);
  console.log(`Taille moyenne par article : ${kbPerArticle.toFixed(2)} KB`);
  
  const avgMonthlyArticles = (novCount + decCount) / 2;
  const monthlySizeMB = (avgMonthlyArticles * kbPerArticle) / 1024;
  const remainingSpaceMB = 500 - 11.4; // 500Mo - (Article + Weather)
  
  const monthsRemaining = remainingSpaceMB / monthlySizeMB;
  const yearsRemaining = monthsRemaining / 12;

  console.log(`--- Extrapolation ---`);
  console.log(`Croissance mensuelle moyenne : ${monthlySizeMB.toFixed(2)} Mo/mois`);
  console.log(`Espace libre : ${remainingSpaceMB.toFixed(2)} Mo`);
  console.log(`Durée de vie estimée : ${yearsRemaining.toFixed(1)} ans`);
}

main()
  .catch((e) => console.error(e))
  .finally(async () => await prisma.$disconnect());
