import { PrismaClient } from '@prisma/client'
const prisma = new PrismaClient()

async function main() {
  const articles = await prisma.article.findMany({
    take: 100,
    orderBy: { publishedAt: 'desc' }
  })

  const seenImageUuids = new Set<string>()
  const seenTitles = new Set<string>()
  const seenImageUrls = new Set<string>()

  console.log(`Initial: ${articles.length} articles`)

  const filtered = articles.filter(article => {
    const cleanTitle = article.title.trim().toLowerCase()
    if (seenTitles.has(cleanTitle)) {
      console.log(`  [X] Doublon TITRE: ${article.title}`)
      return false
    }

    if (article.imageUrl) {
      if (seenImageUrls.has(article.imageUrl)) {
        console.log(`  [X] Doublon IMAGE_URL: ${article.title}`)
        return false
      }
      seenImageUrls.add(article.imageUrl)
    }

    if (article.imageUrl) {
      const match = article.imageUrl.match(/\/images\/([^\/]+)\//)
      if (match) {
        const uuid = match[1]
        if (seenImageUuids.has(uuid)) {
          console.log(`  [X] Doublon UUID: ${article.title}`)
          return false
        }
        seenImageUuids.add(uuid)
      }
    }

    seenTitles.add(cleanTitle)
    return true
  })

  console.log(`Final: ${filtered.length} articles`)
  
  console.log("\nTop 10 après filtrage :")
  filtered.slice(0, 10).forEach(a => console.log(`[${a.source}] ${a.title}`))
}

main().finally(() => prisma.$disconnect())
