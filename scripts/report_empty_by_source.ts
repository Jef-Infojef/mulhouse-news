
import { PrismaClient } from '@prisma/client';
const prisma = new PrismaClient();

async function main() {
  console.log('--- État des articles sans contenu par source ---');

  const stats = await prisma.article.groupBy({
    by: ['source'],
    where: {
      content: null
    },
    _count: {
      id: true
    },
    orderBy: {
      _count: {
        id: 'desc'
      }
    }
  });

  let totalMissing = 0;
  stats.forEach(s => {
    console.log(`${(s.source || 'Inconnue').padEnd(25)} : ${s._count.id} articles vides`);
    totalMissing += s._count.id;
  });

  console.log('\n-------------------------------------------');
  console.log(`TOTAL ARTICLES VIDES       : ${totalMissing}`);
}

main()
  .catch(e => console.error(e))
  .finally(() => prisma.$disconnect());

