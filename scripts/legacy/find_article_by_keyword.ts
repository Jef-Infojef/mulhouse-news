import { PrismaClient } from '@prisma/client';
const prisma = new PrismaClient();

async function findArticleByKeyword() {
  console.log("Recherche d'articles contenant 'sculpture' ou 'police'...");
  const articles = await prisma.article.findMany({
    where: {
      OR: [
        { title: { contains: 'sculpture', mode: 'insensitive' } },
        { title: { contains: 'police', mode: 'insensitive' } }
      ]
    },
    orderBy: { createdAt: 'desc' },
    take: 5
  });

  if (articles.length > 0) {
    articles.forEach(article => {
      console.log("\n--- Article trouvé ---");
      console.log("- Titre :", article.title);
      console.log("- Source :", article.source);
      console.log("- Link :", article.link);
      console.log("- Image URL :", article.imageUrl);
      console.log("- Local Image :", article.localImage);
      console.log("- R2 URL :", article.r2Url);
    });
  } else {
    console.log("Aucun article correspondant trouvé.");
  }
}

findArticleByKeyword().catch(console.error).finally(() => prisma.$disconnect());
