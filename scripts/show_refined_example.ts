
import { PrismaClient } from '@prisma/client';
const prisma = new PrismaClient();

async function main() {
  const art = await prisma.article.findFirst({
    where: { 
      title: { contains: 'On fait quoi ce week-end', mode: 'insensitive' }
    }
  });

  if (art) {
    console.log(`TITRE       : ${art.title}`);
    console.log(`DESCRIPTION : ${art.description}`);
    console.log(`\nDÉBUT DU CONTENU POUR COMPARER :`);
    console.log(art.content?.substring(0, 400));
  }
}

main().finally(() => prisma.$disconnect());

