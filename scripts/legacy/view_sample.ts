import { PrismaClient } from '@prisma/client'

const prisma = new PrismaClient()

async function main() {
  const article = await prisma.article.findFirst({
    where: {
      title: { contains: "Marchés de Noël", mode: 'insensitive' }
    },
    orderBy: { publishedAt: 'desc' }
  })

  if (article) {
    console.log("-----------------------------------------")
    console.log(`TITRE : ${article.title}`)
    console.log("-----------------------------------------")
    console.log("ANCIEN RÉSUMÉ (Description) :")
    console.log(article.description || "Aucune description")
    console.log("-----------------------------------------")
    console.log("NOUVEAU CONTENU (Scrapé) :")
    console.log(article.content)
    console.log("-----------------------------------------")
    console.log(`GAIN DE TEXTE : ${article.content.length - (article.description?.length || 0)} caractères`)
    console.log("-----------------------------------------")
  } else {
    console.log("Aucun article avec contenu trouvé.")
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
