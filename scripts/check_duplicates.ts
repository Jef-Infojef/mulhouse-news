import { PrismaClient } from '@prisma/client'
const prisma = new PrismaClient()

async function main() {
  const articles = await prisma.article.findMany({
    take: 50,
    orderBy: { publishedAt: 'desc' }
  })

  console.log("Derniers articles récupérés :")
  articles.forEach(a => {
    console.log(`[${a.source}] ${a.title}`)
    console.log(`   Image: ${a.imageUrl?.substring(0, 100)}`)
    console.log(`   Link:  ${a.link.substring(0, 100)}`)
    console.log('---')
  })
}

main()
  .catch(console.error)
  .finally(() => prisma.$disconnect())
