import { PrismaClient } from '@prisma/client'

const prisma = new PrismaClient()

async function main() {
  const count = await prisma.article.count({
    where: {
      source: {
        contains: "L'Alsace",
        mode: 'insensitive'
      }
    }
  })
  console.log(`Nombre d'articles de "L'Alsace" : ${count}`)
}

main()
  .catch((e) => {
    console.error(e)
    process.exit(1)
  })
  .finally(async () => {
    await prisma.$disconnect()
  })
