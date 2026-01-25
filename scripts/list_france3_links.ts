import { PrismaClient } from '@prisma/client'

const prisma = new PrismaClient()

async function main() {
  const articles = await prisma.article.findMany({
    where: {
      source: { contains: "France 3", mode: 'insensitive' },
      content: null
    },
    orderBy: { publishedAt: 'desc' },
    take: 3
  })

  console.log("--- Liens France 3 récents ---")
  articles.forEach(a => console.log(a.link))
}

main()
  .catch(console.error)
  .finally(() => prisma.$disconnect())
