import { PrismaClient } from '@prisma/client';
const prisma = new PrismaClient();

function refineText(text: string, limit: number = 250): string {
  if (!text) return "";
  let paragraph = text.split('\n').find(p => p.trim().length > 20) || text.split('\n')[0];
  paragraph = paragraph.trim();

  if (paragraph.length <= limit) return paragraph;

  const sub = paragraph.substring(0, limit);
  // On cherche la dernière ponctuation (. ! ?)
  const lastSentenceEnd = Math.max(
    sub.lastIndexOf('. '),
    sub.lastIndexOf('! '),
    sub.lastIndexOf('? ')
  );

  if (lastSentenceEnd > 100) {
    return paragraph.substring(0, lastSentenceEnd + 1);
  }

  const lastSpace = sub.lastIndexOf(' ');
  if (lastSpace > 150) {
    return paragraph.substring(0, lastSpace) + '...';
  }

  return sub.trim() + '...';
}

async function main() {
  console.log('--- Raffinement CIBLÉ (Uniquement les articles réparés aujourd\'hui) ---');

  // On identifie les articles modifiés aujourd'hui entre 13h00 et maintenant
  const today = new Date();
  today.setHours(13, 0, 0, 0); 

  const articles = await prisma.article.findMany({
    where: {
      updatedAt: { gte: today },
      content: { not: null }
    }
  });

  console.log(`${articles.length} articles identifiés pour raffinement.`);

  for (const art of articles) {
    const newDesc = refineText(art.content || "", 250);
    
    if (newDesc && newDesc !== art.description) {
      await prisma.article.update({
        where: { id: art.id },
        data: { description: newDesc }
      });
      console.log(`✅ Raffiné : ${art.title.substring(0, 50)}...`);
    }
  }
}

main().finally(() => prisma.$disconnect());
