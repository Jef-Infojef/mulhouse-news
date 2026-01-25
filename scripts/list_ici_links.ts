import { PrismaClient } from '@prisma/client'

const prisma = new PrismaClient()

async function main() {
  const articles = await prisma.article.findMany({
    where: {
      OR: [
        { source: { contains: "ici", mode: 'insensitive' } },
        { source: { contains: "Bleu", mode: 'insensitive' } },
        { link: { contains: "francebleu.fr", mode: 'insensitive' } }
      ]
    },
    orderBy: { publishedAt: 'desc' },
    take: 5
  })

  console.log("--- Articles 'ici' / France Bleu trouvés ---")
  articles.forEach(a => {
    console.log(`Source: ${a.source} | Titre: ${a.title}`)
    console.log(`Lien: ${a.link}\n`)
  })
}

main()
  .catch(console.error)
  .finally(() => prisma.$disconnect())

