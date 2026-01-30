import { PrismaClient } from '@prisma/client'

const prisma = new PrismaClient()

async function main() {
  const result = await prisma.article.deleteMany({
    where: {
      link: "https://www.lalsace.fr/culture-loisirs/2026/01/25/marches-de-noel-carnavals-bals-dansants-quel-est-le-prix-a-payer-pour-faire-la-fete"
    }
  })
  console.log(`Nombre d'articles supprimés : ${result.count}`)
}

main()
  .catch((e) => {
    console.error(e)
    process.exit(1)
  })
  .finally(async () => {
    await prisma.$disconnect()
  })
