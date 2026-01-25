import { PrismaClient } from '@prisma/client'

const prisma = new PrismaClient()

async function main() {
  const articles = await prisma.article.findMany({
    where: {
      source: { contains: "France Bleu", mode: 'insensitive' }
    },
    orderBy: { publishedAt: 'desc' },
    take: 3
  })

  console.log("--- Liens France Bleu récents (sans contenu) ---")
  articles.forEach(a => console.log(a.link))
}

main()
  .catch(console.error)
  .finally(() => prisma.$disconnect())
