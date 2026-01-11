import { PrismaClient } from '@prisma/client';

const prisma = new PrismaClient();

async function main() {
  const stats: any = await prisma.$queryRaw`
    SELECT 
      pg_size_pretty(pg_total_relation_size('"Article"')) as article_size,
      pg_size_pretty(pg_total_relation_size('"WeatherHistory"')) as weather_size,
      count(*) as article_count 
    FROM "Article";
  `;
  
  const weatherCount = await prisma.weatherHistory.count();

  console.log('--- Statistiques Base de Données Supabase ---');
  console.log(`Table Article : ${stats[0].article_size} (${stats[0].article_count} lignes)`);
  console.log(`Table WeatherHistory : ${stats[0].weather_size} (${weatherCount} lignes)`);
}

main()
  .catch((e) => console.error(e))
  .finally(async () => await prisma.$disconnect());
