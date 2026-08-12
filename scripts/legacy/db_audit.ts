
import { PrismaClient } from '@prisma/client';
const prisma = new PrismaClient();

async function main() {
  console.log('=== ÉTAT DES LIEUX COMPLET DE LA BASE DE DONNÉES ===\n');

  // 1. Volumes globaux
  const total = await prisma.article.count();
  const withContent = await prisma.article.count({ where: { content: { not: null } } });
  const withImages = await prisma.article.count({ where: { imageUrl: { not: null } } });
  
  console.log(`--- VOLUMES ---\n`);
  console.log(`Total Articles      : ${total}`);
  console.log(`Articles complets   : ${withContent} (${((withContent/total)*100).toFixed(1)}%)`);
  console.log(`Articles avec images: ${withImages} (${((withImages/total)*100).toFixed(1)}%)`);

  // 2. Couverture temporelle
  const oldest = await prisma.article.findFirst({ orderBy: { publishedAt: 'asc' }, select: { publishedAt: true } });
  const newest = await prisma.article.findFirst({ orderBy: { publishedAt: 'desc' }, select: { publishedAt: true } });
  
  console.log(`\n--- COUVERTURE TEMPORELLE ---\n`);
  console.log(`Premier article : ${oldest?.publishedAt.toISOString().split('T')[0]}`);
  console.log(`Dernier article : ${newest?.publishedAt.toISOString().split('T')[0]}`);

  // 3. Top 5 Sources
  const topSources = await prisma.article.groupBy({
    by: ['source'],
    _count: { id: true },
    orderBy: { _count: { id: 'desc' } },
    take: 5
  });

  console.log(`\n--- TOP 5 SOURCES (TOTAL) ---\n`);
  topSources.forEach(s => console.log(`${(s.source || 'Inconnue').padEnd(15)} : ${s._count.id} articles`));

  // 4. Derniers logs de scraping
  const lastLogs = await prisma.scrapingLog.findMany({
    orderBy: { startedAt: 'desc' },
    take: 5
  });

  console.log(`\n--- DERNIERS LOGS DE SCRAPING ---\n`);
  lastLogs.forEach(l => {
    console.log(`${l.startedAt.toISOString().replace('T', ' ').slice(0, 19)} | Status: ${l.status.padEnd(8)} | Arts: ${l.articlesCount} | Succès: ${l.successCount}`);
  });

  // 5. Configuration App
  const configs = await prisma.appConfig.findMany();
  console.log(`\n--- CONFIGURATION ACTIVE ---\n`);
  configs.forEach(c => {
    const val = c.value.length > 50 ? c.value.substring(0, 47) + '...' : c.value;
    console.log(`${c.key.padEnd(15)} : ${val}`);
  });
}

main()
  .catch(e => console.error(e))
  .finally(() => prisma.$disconnect());
