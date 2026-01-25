import { PrismaClient } from '@prisma/client'

const prisma = new PrismaClient()

async function main() {
  const article = await prisma.article.findFirst({
    where: {
      title: { contains: "Élevage intensif de lapins", mode: 'insensitive' }
    }
  })

  if (article) {
    console.log(`TITRE : ${article.title}`)
    console.log(`LIEN  : ${article.link}`)
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
