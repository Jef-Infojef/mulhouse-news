import { PrismaClient } from '@prisma/client'

const prisma = new PrismaClient()

async function main() {
  const articles = await prisma.article.findMany({
    select: {
      publishedAt: true
    },
    orderBy: {
      publishedAt: 'desc'
    }
  })

  const stats: { [key: string]: number } = {}

  articles.forEach(article => {
    if (article.publishedAt) {
      const date = new Date(article.publishedAt)
      const monthYear = `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}`
      stats[monthYear] = (stats[monthYear] || 0) + 1
    } else {
      stats['Inconnu'] = (stats['Inconnu'] || 0) + 1
    }
  })

  console.log('\n--- Rapport des Articles par Mois ---')
  console.log('Mois       | Quantité')
  console.log('-----------|----------')
  
  Object.keys(stats).sort().reverse().forEach(month => {
    console.log(`${month.padEnd(10)} | ${stats[month]}`)
  })
  
  const total = Object.values(stats).reduce((a, b) => a + b, 0)
  console.log('-----------|----------')
  console.log(`TOTAL      | ${total}\n`)
}

main()
  .catch(e => {
    console.error(e)
    process.exit(1)
  })
  .finally(async () => {
    await prisma.$disconnect()
  })

