import { PrismaClient } from '@prisma/client'
const prisma = new PrismaClient()

async function main() {
  const res = await prisma.article.deleteMany({
    where: {
      AND: [
        { source: { contains: 'Ouest-France', mode: 'insensitive' } },
        { title: { contains: 'Météo', mode: 'insensitive' } }
      ]
    }
  })
  console.log(`Supprimé ${res.count} articles météo Ouest-France.`)
}

main().finally(() => prisma.$disconnect())
