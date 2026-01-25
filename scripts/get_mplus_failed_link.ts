import { PrismaClient } from '@prisma/client'

const prisma = new PrismaClient()

async function main() {
  const article = await prisma.article.findFirst({
    where: {
      title: { contains: "Harry Potter", mode: 'insensitive' },
      link: { contains: "mag.mulhouse-alsace.fr" }
    }
  })

  if (article) {
    console.log(article.link)
  }
}

main()
  .catch(console.error)
  .finally(() => prisma.$disconnect())
