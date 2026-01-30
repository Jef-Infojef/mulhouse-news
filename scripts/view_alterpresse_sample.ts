import { PrismaClient } from '@prisma/client'

const prisma = new PrismaClient()

async function main() {
  const article = await prisma.article.findFirst({
    where: {
      link: { contains: "alterpresse68.info" },
      content: { not: null }
    },
    orderBy: { updatedAt: 'desc' }
  })

  if (article) {
    console.log("-----------------------------------------")
    console.log(`TITRE : ${article.title}`)
    console.log("-----------------------------------------")
    console.log("CONTENU RÉCUPÉRÉ :")
    console.log(article.content)
    console.log("-----------------------------------------")
  }
}

main()
  .catch(console.error)
  .finally(() => prisma.$disconnect())
