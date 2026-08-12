import { PrismaClient } from '@prisma/client'

const prisma = new PrismaClient()

async function main() {
  const startDate = new Date('2025-02-25T00:00:00Z')
  
  const articles = await prisma.article.findMany({
    where: {
      publishedAt: {
        gte: startDate
      }
    },
    select: {
      title: true,
      link: true,
      imageUrl: true,
      source: true,
      publishedAt: true
    }
  })

  const total = articles.length
  const googleLinks = articles.filter(a => a.link.includes('google')).length
  const missingImages = articles.filter(a => !a.imageUrl || a.imageUrl.trim() === '').length
  
  console.log(`--- Analyse depuis le 25/02/2025 ---`)
  console.log(`Total articles trouvés : ${total}`)
  console.log(`Articles avec liens Google : ${googleLinks}`)
  console.log(`Articles sans image : ${missingImages}`)
  
  if (total > 0) {
    console.log('\n--- Échantillon des 5 derniers articles ---')
    articles.slice(0, 5).forEach(a => {
      console.log(`Titre  : ${a.title}`)
      console.log(`Source : ${a.source}`)
      console.log(`Lien   : ${a.link}`)
      console.log(`Image  : ${a.imageUrl || 'MANQUANTE'}`)
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
