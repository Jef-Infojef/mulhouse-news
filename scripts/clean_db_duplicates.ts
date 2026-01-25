import { PrismaClient } from '@prisma/client';

const prisma = new PrismaClient();

async function cleanDuplicates() {
  console.log('--- Nettoyage des doublons d\'articles (Titre & Image) ---');

  // 1. Doublons par TITRE
  const titleDuplicates: any[] = await prisma.$queryRaw`
    SELECT title, COUNT(*) as count
    FROM "Article"
    GROUP BY title
    HAVING COUNT(*) > 1;
  `;

  console.log(`${titleDuplicates.length} groupes de doublons par titre identifiés.`);

  for (const group of titleDuplicates) {
    const articles = await prisma.article.findMany({
      where: { title: group.title },
      orderBy: [{ content: 'desc' }, { publishedAt: 'desc' }]
    });
    if (articles.length > 1) {
      const toDelete = articles.slice(1).map(a => a.id);
      await prisma.article.deleteMany({ where: { id: { in: toDelete } } });
      console.log(`[OK] Supprimé ${toDelete.length} doublon(s) pour le titre: "${group.title.substring(0, 50)}"...`);
    }
  }

  // 2. Doublons par IMAGE URL (ignorer les images génériques)
  const imageDuplicates: any[] = await prisma.$queryRaw`
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
${imageDuplicates.length} groupes de doublons par URL d'image identifiés.`);

  let imgDeleted = 0;
  for (const group of imageDuplicates) {
    const articles = await prisma.article.findMany({
      where: { imageUrl: group.imageUrl },
      orderBy: [{ content: 'desc' }, { publishedAt: 'desc' }]
    });
    if (articles.length > 1) {
      const toDelete = articles.slice(1).map(a => a.id);
      const res = await prisma.article.deleteMany({ where: { id: { in: toDelete } } });
      imgDeleted += res.count;
      console.log(`[OK] Supprimé ${res.count} doublon(s) pour l'image: "${group.imageUrl.substring(0, 60)}"...`);
    }
  }

  console.log(`
Fini ! Total images supprimées : ${imgDeleted}`);
}

cleanDuplicates()
  .catch(e => console.error(e))
  .finally(async () => await prisma.$disconnect());
