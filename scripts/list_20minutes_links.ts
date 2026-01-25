import { PrismaClient } from '@prisma/client'

const prisma = new PrismaClient()

async function main() {
  const articles = await prisma.article.findMany({
    where: {
      OR: [
        { source: { contains: "20 Minutes", mode: 'insensitive' } },
        { link: { contains: "20minutes.fr", mode: 'insensitive' } }
      ],
      content: null
    },
    orderBy: { publishedAt: 'desc' },
    take: 3
  })

  console.log("--- Liens 20 Minutes récents ---")
  articles.forEach(a => console.log(a.link))
}

main()
  .catch(console.error)
  .finally(() => prisma.$disconnect())
