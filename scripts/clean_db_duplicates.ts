import { PrismaClient } from '@prisma/client';

const prisma = new PrismaClient();

async function cleanDuplicates() {
  console.log('--- Nettoyage intelligent des doublons (Même Image ET Même Jour) ---');

  // 1. Doublons par TITRE (Règle stricte : même titre = doublon)
  const titleDuplicates: any[] = await prisma.$queryRaw`
    SELECT title, COUNT(*) as count
    FROM "Article"
    GROUP BY title
    HAVING COUNT(*) > 1;
  `;

  console.log(`${titleDuplicates.length} titres en double identifiés.`);
  for (const group of titleDuplicates) {
    const articles = await prisma.article.findMany({
      where: { title: group.title },
      orderBy: [{ content: 'desc' }, { publishedAt: 'desc' }]
    });
    if (articles.length > 1) {
      const toDelete = articles.slice(1).map(a => a.id);
      await prisma.article.deleteMany({ where: { id: { in: toDelete } } });
    }
  }

  // 2. Doublons par IMAGE URL + MÊME JOUR
  // On récupère les articles qui partagent la même image (hors logos/placeholders)
  const imageGroups: any[] = await prisma.$queryRaw`
    SELECT "imageUrl", COUNT(*) as count
    FROM "Article"
    WHERE "imageUrl" IS NOT NULL 
      AND "imageUrl" <> '' 
      AND "imageUrl" <> 'null'
      AND "imageUrl" NOT ILIKE '%logo%'
      AND "imageUrl" NOT ILIKE '%placeholder%'
      AND "imageUrl" NOT ILIKE '%default%'
      AND "imageUrl" NOT ILIKE '%header%'
      AND "imageUrl" NOT ILIKE 'image.png'
    GROUP BY "imageUrl"
    HAVING COUNT(*) > 1;
  `;

  console.log(`
${imageGroups.length} images partagées identifiées.`);

  let totalDeleted = 0;

  for (const group of imageGroups) {
    const articles = await prisma.article.findMany({
      where: { imageUrl: group.imageUrl },
      orderBy: { publishedAt: 'desc' }
    });

    // On va grouper ces articles par DATE (jour uniquement)
    const byDay: { [key: string]: any[] } = {};
    
    articles.forEach(art => {
      const day = new Date(art.publishedAt).toISOString().split('T')[0];
      if (!byDay[day]) byDay[day] = [];
      byDay[day].push(art);
    });

    // Pour chaque jour, si on a plus d'un article avec cette image, on ne garde que le premier (le plus récent ou celui avec contenu)
    for (const day in byDay) {
      const dayArticles = byDay[day];
      if (dayArticles.length > 1) {
        // Trier pour garder celui qui a du contenu
        dayArticles.sort((a, b) => (b.content?.length || 0) - (a.content?.length || 0));
        
        const toKeep = dayArticles[0];
        const toDeleteIds = dayArticles.slice(1).map(a => a.id);
        
        const res = await prisma.article.deleteMany({
          where: { id: { in: toDeleteIds } }
        });
        
        totalDeleted += res.count;
        console.log(`[CLEAN] Image: ${group.imageUrl.substring(0, 40)}... | Jour: ${day} | Supprimés: ${res.count}`);
      }
    }
  }

  console.log(`
Fini ! Total doublons (image + jour) supprimés : ${totalDeleted}`);
}

cleanDuplicates()
  .catch(e => console.error(e))
  .finally(async () => await prisma.$disconnect());