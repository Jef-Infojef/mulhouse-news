import { PrismaClient } from '@prisma/client'

const prisma = new PrismaClient()

async function main() {
  const day = new Date('2025-02-25T00:00:00Z')
  const nextDay = new Date('2025-02-26T00:00:00Z')
  
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

  console.log(`Nombre d'articles le 25/02/2025: ${articles.length}`)
  console.log('---')
  
  articles.forEach((a, i) => {
    console.log(`${i+1}. [${a.source}] ${a.title}`)
    console.log(`   Lien: ${a.link.substring(0, 80)}...`)
    console.log(`   Image: ${a.imageUrl ? 'OUI' : 'NON'}`)
    if (a.link.includes('google')) console.log(`   ⚠️ LIEN GOOGLE DETECTÉ`)
    console.log('---')
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
