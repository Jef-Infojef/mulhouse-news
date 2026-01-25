import { PrismaClient } from '@prisma/client'

const prisma = new PrismaClient()

async function main() {
  const articles = await prisma.article.findMany({
    where: {
      OR: [
        { source: { contains: "Le Parisien", mode: 'insensitive' } },
        { link: { contains: "leparisien.fr", mode: 'insensitive' } }
      ],
      content: null
    },
    orderBy: { publishedAt: 'desc' },
    take: 3
  })

  console.log("--- Liens Le Parisien récents ---")
  articles.forEach(a => console.log(a.link))
}

main()
  .catch(console.error)
  .finally(() => prisma.$disconnect())
