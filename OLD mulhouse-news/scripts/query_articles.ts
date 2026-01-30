
import { PrismaClient } from '@prisma/client'

const prisma = new PrismaClient()

async function main() {
  const sources = await prisma.article.groupBy({
    by: ['source'],
  })

  console.log('Unique sources:')
  sources.forEach(s => console.log(`- ${s.source}`))
}

main()
  .catch(e => console.error(e))
  .finally(async () => await prisma.$disconnect())
