import { PrismaClient } from '@prisma/client'

const prisma = new PrismaClient()

async function main() {
  const startMarch = new Date('2025-03-01T00:00:00Z')
  const endMarch = new Date('2025-03-31T23:59:59Z')
  
  const count = await prisma.article.count({
    where: {
      publishedAt: {
        gte: startMarch,
        lte: endMarch
      }
    }
  })

  const sample = await prisma.article.findMany({
    where: {
      publishedAt: {
        gte: startMarch,
        lte: endMarch
      }
    },
    orderBy: {
      publishedAt: 'asc'
    },
    take: 5,
    select: {
      title: true,
      link: true,
      publishedAt: true,
      source: true
    }
  })

  console.log(`Nombre d'articles en mars 2025: ${count}`)
  if (count > 0) {
    console.log('\nPremiers articles de mars trouvés:')
    sample.forEach(a => {
      console.log(`- [${a.publishedAt?.toISOString().split('T')[0]}] ${a.title} (${a.source})`)
    })
  } else {
    console.log('\nAucun article trouvé pour mars 2025.')
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
