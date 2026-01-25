import { PrismaClient } from '@prisma/client';

const prisma = new PrismaClient();

async function cleanDuplicates() {
  console.log('--- Nettoyage des doublons d\'articles ---');

  // 1. Identifier les groupes de doublons (même titre)
  const duplicates: any[] = await prisma.$queryRaw`
    SELECT title, COUNT(*) as count
    FROM "Article"
    GROUP BY title
    HAVING COUNT(*) > 1
    ORDER BY count DESC;
  `;

  console.log(`${duplicates.length} titres en double identifiés.`);

  let totalDeleted = 0;

  for (const group of duplicates) {
    const title = group.title;
    
    // Récupérer tous les articles avec ce titre
    const articles = await prisma.article.findMany({
      where: { title: title },
      orderBy: [
        { content: 'desc' }, // Garder celui qui a du contenu en priorité
        { publishedAt: 'desc' }
      ]
    });

    if (articles.length <= 1) continue;

    // Le premier est celui qu'on garde
    const toKeep = articles[0];
    const toDeleteIds = articles.slice(1).map(a => a.id);

    // Suppression
    const result = await prisma.article.deleteMany({
      where: {
        id: { in: toDeleteIds }
      }
    });

    totalDeleted += result.count;
    console.log(`[OK] Titre: "${title.substring(0, 50)}"..." | Gardé: ${toKeep.id} | Supprimés: ${result.count}`);
  }

  console.log(`
Fini ! Total supprimés : ${totalDeleted}`);
}

cleanDuplicates()
  .catch(e => console.error(e))
  .finally(async () => await prisma.$disconnect());