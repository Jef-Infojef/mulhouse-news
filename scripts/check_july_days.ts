import { PrismaClient } from '@prisma/client';

const prisma = new PrismaClient();

async function main() {
  const stats: any = await prisma.$queryRaw`
    SELECT 
      EXTRACT(DAY FROM "publishedAt") as day,
      COUNT(*) as count
    FROM "Article"
    WHERE "publishedAt" >= '2025-07-01' AND "publishedAt" <= '2025-07-31'
    GROUP BY day
    ORDER BY day ASC;
  `;

  console.log('--- Calendrier Juillet 2025 ---');
  const daysPresent = stats.map((s: any) => Number(s.day));
  
  let output = "";
  for (let i = 1; i <= 31; i++) {
    const found = stats.find((s: any) => Number(s.day) === i);
    const count = found ? Number(found.count) : 0;
    const marker = count > 0 ? `[${count.toString().padStart(2, ' ')}]` : "[--]";
    output += marker + (i % 7 === 0 ? "\n" : " ");
  }
  
  console.log(output);
  console.log('\n[--] = Aucun article | [Nb] = Nombre d\'articles');
  console.log(`Jours avec articles : ${daysPresent.length}/31`);
}

main()
  .catch(console.error)
  .finally(() => prisma.$disconnect());
