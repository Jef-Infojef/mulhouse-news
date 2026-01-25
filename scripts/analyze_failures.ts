import { PrismaClient } from '@prisma/client'

const prisma = new PrismaClient()

async function main() {
  const startDate = new Date('2026-01-01T00:00:00Z')
  const endDate = new Date('2026-02-01T00:00:00Z')

  const failures = await prisma.article.findMany({
    where: {
      source: { contains: "Alsace", mode: 'insensitive' },
      publishedAt: { gte: startDate, lt: endDate },
      OR: [
        { content: null },
        { content: { equals: "" } } // Prisma ne supporte pas length < 500 direct ici facilement sans raw query
      ]
    },
    select: {
      title: true,
      link: true,
      source: true
    }
  })

  // On filtre manuellement les contenus trop courts si besoin, mais ici on regarde surtout les NULL
  console.log(`=== ANALYSE DES ÉCHECS JANVIER 2026 (${failures.length} articles) ===`)
  
  const domains: {[key: string]: number} = {}
  const types: {[key: string]: number} = {}

  failures.forEach(f => {
    // Analyse du domaine/sous-domaine
    try {
        const url = new URL(f.link)
        const hostname = url.hostname
        domains[hostname] = (domains[hostname] || 0) + 1
        
        // Analyse des segments d'URL pour deviner le type
        const path = url.pathname
        const firstSegment = path.split('/')[1] || 'root'
        types[firstSegment] = (types[firstSegment] || 0) + 1

    } catch (e) {
        console.log(`URL Invalide: ${f.link}`)
    }
  })

  console.log("\n--- Répartition par Domaine ---")
  console.table(domains)

  console.log("\n--- Répartition par Section (URL) ---")
  console.table(types)

  console.log("\n--- Exemples d'URLs en échec ---")
  failures.slice(0, 10).forEach(f => console.log(`- ${f.link}`))
}

main()
  .catch((e) => {
    console.error(e)
    process.exit(1)
  })
  .finally(async () => {
    await prisma.$disconnect()
  })
