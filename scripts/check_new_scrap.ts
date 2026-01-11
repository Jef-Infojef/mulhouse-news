import { PrismaClient } from '@prisma/client'

const prisma = new PrismaClient()

async function main() {
  const startDate = new Date('2025-02-25T00:00:00Z')
  
  const count = await prisma.article.count({
    where: {
      publishedAt: {
        gte: startDate
      }
    }
  })

  const latestArticles = await prisma.article.findMany({
    where: {
      publishedAt: {
        gte: startDate
      }
    },
    orderBy: {
      publishedAt: 'desc'
    },
    take: 5,
    select: {
      title: true,
      link: true,
      publishedAt: true,
      source: true
    }
  })

  console.log(`Nombre d'articles à partir du 25/02/2025: ${count}`)
  console.log('\nExemple des derniers articles scrapés:')
  latestArticles.forEach(a => {
    console.log(`- [${a.publishedAt?.toISOString().split('T')[0]}] ${a.title} (${a.source})`)
    console.log(`  Lien: ${a.link}`)
  })
}

main()
  .catch(e => {
    console.error(e)
    process.exit(1)
  })
  .finally(async () => {
    await prisma.$disconnect()
  })

