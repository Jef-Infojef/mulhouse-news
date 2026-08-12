import { PrismaClient } from '@prisma/client'

const prisma = new PrismaClient()

async function main() {
  const startDate = new Date('2026-01-01T00:00:00Z')
  const endDate = new Date('2026-02-01T00:00:00Z')

  const total = await prisma.article.count({
    where: {
      source: { contains: "Alsace", mode: 'insensitive' },
      publishedAt: { gte: startDate, lt: endDate }
    }
  })

  const fullContent = await prisma.article.count({
    where: {
      source: { contains: "Alsace", mode: 'insensitive' },
      publishedAt: { gte: startDate, lt: endDate },
      // On considère "complet" s'il a plus de 500 caractères (pour éviter juste les titres/chapôs courts)
      // Note: Prisma ne permet pas length filter direct facilement en standard, on vérifie non null d'abord
      content: { not: null }
    }
  })

  // Pour affiner, on récupère les articles avec content et on filtre en JS (sur un petit volume ça va)
  const articlesWithContent = await prisma.article.findMany({
    where: {
      source: { contains: "Alsace", mode: 'insensitive' },
      publishedAt: { gte: startDate, lt: endDate },
      content: { not: null }
    },
    select: { id: true, content: true }
  })

  const reallyFull = articlesWithContent.filter(a => (a.content?.length || 0) > 500).length
  const partial = articlesWithContent.filter(a => (a.content?.length || 0) <= 500).length
  const empty = total - articlesWithContent.length

  console.log("=== ÉTAT DES LIEUX L'ALSACE - JANVIER 2026 ===")
  console.log(`Total articles       : ${total}`)
  console.log(`----------------------------------------------`)
  console.log(`✅ Contenu complet    : ${reallyFull}  (${Math.round(reallyFull/total*100)}%)`)
  console.log(`⚠️ Contenu partiel    : ${partial}   (Chapô uniquement ?)`)
  console.log(`❌ Sans contenu       : ${empty}     (À traiter)`)
  console.log(`----------------------------------------------`)
}

main()
  .catch((e) => {
    console.error(e)
    process.exit(1)
  })
  .finally(async () => {
    await prisma.$disconnect()
  })
