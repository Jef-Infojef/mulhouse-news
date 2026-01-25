import { PrismaClient } from '@prisma/client'

const prisma = new PrismaClient()

async function main() {
  const article = await prisma.article.findFirst({
    where: {
      source: { contains: "Alsace", mode: 'insensitive' },
      content: { contains: "Soirées" } // Pour cibler Confé' Soirées par exemple
    }
  })

  if (article) {
    console.log(`TITRE : ${article.title}`)
    console.log(`TAILLE: ${article.content?.length} chars`)
    console.log(`CONTENU : [${article.content}]`)
  } else {
    console.log("Article non trouvé.")
  }
}

main()
  .catch((e) => {
    console.error(e)
    process.exit(1)
  })
  .finally(async () => {
    await prisma.$disconnect()
  })
