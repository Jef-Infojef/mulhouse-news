import { PrismaClient } from '@prisma/client';
const prisma = new PrismaClient();

function refineText(text: string, limit: number = 250): string {
  if (!text) return "";
  
  // 1. On prend le premier paragraphe significatif
  let paragraph = text.split('\n').find(p => p.trim().length > 20) || text.split('\n')[0];
  paragraph = paragraph.trim();

  if (paragraph.length <= limit) return paragraph;

  // 2. On cherche la dernière ponctuation de fin de phrase dans la limite
  const sub = paragraph.substring(0, limit);
  const lastSentenceEnd = Math.max(
    sub.lastIndexOf('. '),
    sub.lastIndexOf('! '),
    sub.lastIndexOf('? ')
  );

  // Si on trouve une fin de phrase après au moins 100 caractères, on coupe là
  if (lastSentenceEnd > 100) {
    return paragraph.substring(0, lastSentenceEnd + 1);
  }

  // 3. Sinon, on coupe au dernier espace avant la limite pour ne pas couper un mot
  const lastSpace = sub.lastIndexOf(' ');
  if (lastSpace > 150) {
    return paragraph.substring(0, lastSpace) + '...';
  }

  // 4. Fallback ultime
  return sub.trim() + '...';
}

async function main() {
  console.log('--- Raffinement des descriptions (Fin de phrase intelligente) ---');

  const articles = await prisma.article.findMany({
    where: {
      content: { not: null },
      // On cible surtout ceux qui finissent par "..." car ce sont nos extraits
      description: { endsWith: '...' }
    }
  });

  console.log(`Analyse de ${articles.length} articles...`);
  let updated = 0;

  for (const art of articles) {
    const oldDesc = art.description || "";
    const newDesc = refineText(art.content || "", 250);

    if (newDesc && newDesc !== oldDesc) {
      await prisma.article.update({
        where: { id: art.id },
        data: { description: newDesc }
      });
      updated++;
      console.log(`  ✨ Raffiné: ${art.title.substring(0, 40)}...`);
      console.log(`     [AVANT] ${oldDesc.substring(0, 60)}...`);
      console.log(`     [APRÈS] ${newDesc.substring(0, 60)}...`);
    }
  }

  console.log(`\n✅ Terminé. ${updated} descriptions ont été raffinées.`);
}

main().finally(() => prisma.$disconnect());
