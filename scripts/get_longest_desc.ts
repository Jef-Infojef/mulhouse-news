import { PrismaClient } from '@prisma/client';

const prisma = new PrismaClient();

async function main() {
  const stats: any = await prisma.$queryRaw`
    SELECT title, source, description, LENGTH(description) as len
    FROM "Article"
    WHERE description IS NOT NULL
    ORDER BY len DESC
    LIMIT 1;
  `;

  if (stats.length > 0) {
    const a = stats[0];
    console.log('--- Description la plus longue ---');
    console.log(`Titre : ${a.title}`);
    console.log(`Source : ${a.source}`);
    console.log(`Longueur : ${a.len} caractères`);
    console.log(`\nContenu :\n${a.description}`);
  } else {
    console.log('Aucune description trouvée.');
  }
}

main()
  .catch(console.error)
  .finally(() => prisma.$disconnect());

