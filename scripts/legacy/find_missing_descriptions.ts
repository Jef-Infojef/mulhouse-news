import { PrismaClient } from '@prisma/client';
const prisma = new PrismaClient();

async function findMissingDescriptions() {
  console.log("Recherche des articles sans description...");
  const articles = await prisma.article.findMany({
    where: {
      OR: [
        { description: null },
        { description: "" }
      ]
    },
    orderBy: { createdAt: 'desc' },
    take: 10
  });

  if (articles.length > 0) {
    articles.forEach(article => {
      console.log("\n--- Article trouvé ---");
      console.log("- Titre :", article.title);
      console.log("- Source :", article.source);
      console.log("- Link :", article.link);
      console.log("- Description :", article.description);
      console.log("- Image URL :", article.imageUrl);
    });
  } else {
    console.log("Aucun article avec description manquante trouvé.");
  }
}

findMissingDescriptions().catch(console.error).finally(() => prisma.$disconnect());