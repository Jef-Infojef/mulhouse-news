import { PrismaClient } from '@prisma/client';

const prisma = new PrismaClient();

async function main() {
  const articles = await prisma.article.findMany({
    where: {
      imageUrl: { contains: '/images/' }
    },
    orderBy: { publishedAt: 'desc' },
    take: 200
  });

  console.log('--- Comparaison des UUID d\'images EBRA ---');
  
  const uuidMap = new Map();

  for (const a of articles) {
    const url = a.imageUrl || '';
    const match = url.match(/\/images\/([^\/]+)\//);
    if (match) {
      const uuid = match[1];
      if (!uuidMap.has(uuid)) uuidMap.set(uuid, []);
      uuidMap.get(uuid).push(a);
    }
  }

  let matchFound = false;
  for (const [uuid, arts] of uuidMap.entries()) {
    if (arts.length > 1) {
      const sources = arts.map((a: any) => a.source);
      const hasDNA = sources.some((s: string) => s && s.includes('DNA'));
      const hasAlsace = sources.some((s: string) => s && s.includes('Alsace'));

      if (hasDNA && hasAlsace) {
        matchFound = true;
        console.log(`✅ Doublon trouvé pour l\'UUID image: ${uuid}`);
        for (const a of arts) {
          console.log(`   - [${a.source}] ${a.title.substring(0, 60)}...`);
        }
        console.log('');
      }
    }
  }

  if (!matchFound) {
    console.log('❌ Aucun doublon d\'image identique trouvé entre DNA et Alsace sur les 200 derniers articles.');
  }
}

main()
  .catch(console.error)
  .finally(() => prisma.$disconnect());
