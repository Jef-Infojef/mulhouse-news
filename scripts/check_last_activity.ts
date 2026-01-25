import { PrismaClient } from '@prisma/client'
const prisma = new PrismaClient()

async function main() {
  const articles = await prisma.article.findMany({
    take: 10,
    orderBy: { scrapedAt: 'desc' }
  })
  console.log("Derniers articles scrapés (date locale de l'agent) :\n")
  articles.forEach(a => {
    console.log(`[${a.scrapedAt.toISOString()}] ${a.title.substring(0, 80)}`)
  })
}
main().finally(() => prisma.$disconnect())
