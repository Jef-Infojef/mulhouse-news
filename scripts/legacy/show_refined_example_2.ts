
import { PrismaClient } from '@prisma/client';
const prisma = new PrismaClient();

async function main() {
  const art = await prisma.article.findFirst({
    where: { 
      title: { contains: 'Michèle Lutz', mode: 'insensitive' }
    }
  });

  if (art) {
    console.log(`TITRE       : ${art.title}`);
    console.log(`DESCRIPTION : ${art.description}`);
  }
}

main().finally(() => prisma.$disconnect());
