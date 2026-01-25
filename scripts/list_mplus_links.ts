import { PrismaClient } from '@prisma/client'

const prisma = new PrismaClient()

async function main() {
  const articles = await prisma.article.findMany({
    where: {
      link: { contains: "mag.mulhouse-alsace.fr" }
    },
    orderBy: { publishedAt: 'desc' },
    take: 3
  })

  console.log("--- Liens M+ récents ---")
  articles.forEach(a => console.log(a.link))
}

main()
  .catch(console.error)
  .finally(() => prisma.$disconnect())
