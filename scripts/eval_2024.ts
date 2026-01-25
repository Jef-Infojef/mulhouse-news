import { PrismaClient } from '@prisma/client';

const prisma = new PrismaClient({
  datasources: {
    db: {
      url: "postgresql://postgres.wmvjpdedrfyttixdkzpi:05v0Ije8JayPNsaI@aws-1-eu-west-3.pooler.supabase.com:5432/postgres"
    },
  },
});

async function main() {
  const year = 2024;
  const start = new Date(`${year}-01-01`);
  const end = new Date(`${year}-12-31`);

  const stats: any = await prisma.$queryRaw`
    SELECT 
      COUNT(DISTINCT TO_CHAR("publishedAt", 'YYYY-MM-DD')) as days_present,
      COUNT(*) as total_articles
    FROM "Article"
    WHERE "publishedAt" >= ${start} AND "publishedAt" <= ${end};
  `;

  const daysPresent = Number(stats[0].days_present);
  const articlesPresent = Number(stats[0].total_articles);
  const avgPerDay = daysPresent > 0 ? (articlesPresent / daysPresent) : 0;

  const totalDaysInYear = 366;
  const estimatedTotalArticles = Math.round(totalDaysInYear * avgPerDay);
  const missingArticles = estimatedTotalArticles - articlesPresent;

  console.log(`--- Évaluation Année 2024 ---`);
  console.log(`Articles déjà présents : ${articlesPresent}`);
  console.log(`Jours déjà couverts    : ${daysPresent}/${totalDaysInYear}`);
  console.log(`Moyenne par jour       : ${avgPerDay.toFixed(1)} articles`);
  console.log(`-----------------------------`);
  console.log(`Estimation Totale 2024 : ${estimatedTotalArticles} articles`);
  console.log(`Reste à scrapper       : ~${missingArticles} articles`);
  console.log(`Poids estimé (2Ko/art) : ~${(estimatedTotalArticles * 2 / 1024).toFixed(2)} Mo`);
}

main()
  .catch((e) => console.error(e))
  .finally(async () => await prisma.$disconnect());