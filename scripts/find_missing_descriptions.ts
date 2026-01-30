
import { PrismaClient } from '@prisma/client';
const prisma = new PrismaClient();

async function main() {
  const count = await prisma.article.count({
    where: {
      content: { not: null },
      description: null
    }
  });

  console.log(`Nombre d'articles avec contenu mais SANS description : ${count}`);

  if (count > 0) {
    const samples = await prisma.article.findMany({
      where: {
        content: { not: null },
        description: null
      },
      take: 5,
      select: { title: true, source: true, publishedAt: true }
    });
    console.log('\nExemples :');
    samples.forEach(s => console.log(`- [${s.source}] ${s.title} (${s.publishedAt.toISOString().split('T')[0]})`));
  }
}

main().finally(() => prisma.$disconnect());
