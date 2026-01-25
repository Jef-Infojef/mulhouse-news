import { PrismaClient } from '@prisma/client'

const prisma = new PrismaClient()

async function main() {
  // On liste toutes les sources distinctes
  const articles = await prisma.article.groupBy({
    by: ['source'],
    _count: {
      id: true
    }
  })

  console.log("--- SOURCES PRÉSENTES EN BASE ---")
  articles.forEach(a => {
    console.log(`[${a._count.id}] ${a.source || 'Inconnu'}`)
  })
}

main()
  .catch(console.error)
  .finally(() => prisma.$disconnect())
