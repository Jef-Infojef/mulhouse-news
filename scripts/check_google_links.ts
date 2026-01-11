import { PrismaClient } from '@prisma/client'

const prisma = new PrismaClient()

async function main() {
  const googleArticles = await prisma.article.findMany({
    where: {
      link: {
        contains: 'google'
      }
    },
    take: 10,
    select: {
      link: true
    }
  })

  console.log('Articles avec liens Google found:', googleArticles.length)
  googleArticles.forEach(a => console.log(a.link))
}

main()
  .catch(e => {
    console.error(e)
    process.exit(1)
  })
  .finally(async () => {
    await prisma.$disconnect()
  })
