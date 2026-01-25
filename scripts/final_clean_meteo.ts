import { PrismaClient } from '@prisma/client'
const prisma = new PrismaClient()

async function main() {
  const articles = await prisma.article.findMany({
    where: {
      OR: [
        { 
          AND: [
            { source: { contains: 'Ouest-France', mode: 'insensitive' } },
            { title: { contains: 'Météo', mode: 'insensitive' } }
          ]
        },
        { title: { contains: 'Météo. Quel temps', mode: 'insensitive' } }
      ]
    }
  })
  
  if (articles.length > 0) {
    console.log(`Suppression de ${articles.length} articles supplémentaires...`)
    await prisma.article.deleteMany({
      where: { id: { in: articles.map(a => a.id) } }
    })
  } else {
    console.log("Aucun article météo Ouest-France trouvé.")
  }
}

main().finally(() => prisma.$disconnect())
