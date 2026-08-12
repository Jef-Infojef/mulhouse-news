import { PrismaClient } from '@prisma/client'
const prisma = new PrismaClient()

async function main() {
  const ids = [
    'd5c1dc5f-76d5-4d30-a702-ac8066740df6', // ID approximatif, je vais utiliser les titres
  ]
  
  const search = [
    'Yannick Konki quitte le FC Mulhouse',
    'Mission accomplie pour le Volley Mulhouse',
    'Après un premier set perdu, le VMA balaye'
  ]
  
  const articles = await prisma.article.findMany({
    where: {
      OR: search.map(s => ({ title: { contains: s } }))
    }
  })
  
  console.log(`Resetting ${articles.length} articles...`)
  await prisma.article.updateMany({
    where: { id: { in: articles.map(a => a.id) } },
    data: { content: null }
  })
}

main().finally(() => prisma.$disconnect())
