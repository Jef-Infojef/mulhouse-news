import { PrismaClient } from '@prisma/client';

const prisma = new PrismaClient();

async function comparePhotos() {
  const query = "Volley Mulhouse Alsace%";
  const articles = await prisma.article.findMany({
    where: {
      title: { contains: 'Volley Mulhouse Alsace' }
    },
    take: 10,
    select: {
      title: true,
      source: true,
      imageUrl: true
    }
  });

  console.log('--- Comparaison Photos DNA vs L\'Alsace ---');
  articles.forEach(a => {
    console.log(`- [${a.source}] ${a.title.substring(0, 50)}...`);
    console.log(`  Photo: ${a.imageUrl?.split('?')[0] || 'Aucune'}\n`);
  });
}

comparePhotos()
  .catch((e) => console.error(e))
  .finally(async () => await prisma.$disconnect());
