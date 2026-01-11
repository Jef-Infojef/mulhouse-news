import { PrismaClient } from '@prisma/client'

const prisma = new PrismaClient()

async function main() {
  const day = new Date('2025-03-01T00:00:00Z')
  const nextDay = new Date('2025-03-02T00:00:00Z')
  
  const articles = await prisma.article.findMany({
    where: {
      publishedAt: {
        gte: day,
        lt: nextDay
      }
    },
    orderBy: {
      publishedAt: 'asc'
    }
  })

  console.log(`Nombre d'articles le 01/03/2025: ${articles.length}`)
  if (articles.length > 0) {
    articles.forEach((a, i) => {
      console.log(`${i+1}. [${a.source}] ${a.title}`)
      console.log(`   Lien: ${a.link}`)
      console.log(`   Image: ${a.imageUrl ? 'OUI' : 'NON'}`)
      console.log('---')
    })
  }
}

main()
  .catch(e => {
    console.error(e)
    process.exit(1)
  })
  .finally(async () => {
    await prisma.$disconnect()
  })
