import { PrismaClient } from '@prisma/client'

const prisma = new PrismaClient()

async function main() {
  const startDate = new Date('2025-12-01T00:00:00Z')
  const endDate = new Date('2026-01-01T00:00:00Z')

  const count = await prisma.article.count({
    where: {
      source: { contains: "Alsace", mode: 'insensitive' },
      publishedAt: {
        gte: startDate,
        lt: endDate
      }
    }
  })
  console.log(`Nombre d'articles de "L'Alsace" en décembre 2025 : ${count}`)
}

main()
  .catch((e) => {
    console.error(e)
    process.exit(1)
  })
  .finally(async () => {
    await prisma.$disconnect()
  })
