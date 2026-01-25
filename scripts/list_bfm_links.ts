import { PrismaClient } from '@prisma/client'

const prisma = new PrismaClient()

async function main() {
  const articles = await prisma.article.findMany({
    where: {
      OR: [
        { source: { contains: "BFM", mode: 'insensitive' } },
        { link: { contains: "bfmtv.com", mode: 'insensitive' } }
      ],
      content: null
    },
    orderBy: { publishedAt: 'desc' },
    take: 3
  })

  console.log("--- Liens BFM récents ---")
  articles.forEach(a => console.log(a.link))
}

main()
  .catch(console.error)
  .finally(() => prisma.$disconnect())
