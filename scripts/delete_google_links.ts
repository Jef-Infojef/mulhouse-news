import { PrismaClient } from '@prisma/client'

const prisma = new PrismaClient()

async function main() {
  const result = await prisma.article.deleteMany({
    where: {
      link: {
        contains: 'google'
      }
    }
  })

  console.log(`Suppression terminée. Nombre d'articles supprimés : ${result.count}`)
}

main()
  .catch(e => {
    console.error(e)
    process.exit(1)
  })
  .finally(async () => {
    await prisma.$disconnect()
  })
