import { PrismaClient } from '@prisma/client'

const prisma = new PrismaClient()

async function main() {
  const article = await prisma.article.findFirst({
    where: {
      title: { contains: "Le samedi, ça vous dit", mode: 'insensitive' }
    }
  })

  if (article) {
    console.log(article.link)
  }
}

main()
  .catch((e) => { console.error(e); process.exit(1) })
  .finally(async () => { await prisma.$disconnect() })
