import { PrismaClient } from '@prisma/client'
const prisma = new PrismaClient()

async function main() {
  const start = new Date('2026-01-01T00:00:00.000Z')
  const end = new Date('2026-02-01T00:00:00.000Z')

  console.log('=== ÉTAT DES LIEUX : JANVIER 2026 ===\n')

  // 1. Total Articles
  const total = await prisma.article.count({
    where: { publishedAt: { gte: start, lt: end } }
  })
  console.log(`TOTAL ARTICLES : ${total}`)

  // 2. Répartition par Source
  const bySource = await prisma.article.groupBy({
    by: ['source'],
    where: { publishedAt: { gte: start, lt: end } },
    _count: { id: true },
    orderBy: { _count: { id: 'desc' } }
  })

  console.log('\n--- Par Source ---')
  bySource.forEach(s => {
    console.log(`${(s.source || 'Inconnu').padEnd(30)} : ${s._count.id}`)
  })

  // 3. Qualité du Contenu (Articles courts / Fallback)
  const shortContent = await prisma.article.count({
    where: {
      publishedAt: { gte: start, lt: end },
      OR: [{ content: null }, { content: '' }]
    }
  })
  
  // On doit filtrer la longueur en post-traitement ou raw query pour être précis sur la longueur
  // On va faire un count sur ceux qui ont du contenu mais < 500 chars
  const allContent = await prisma.article.findMany({
    where: { 
      publishedAt: { gte: start, lt: end },
      content: { not: null }
    },
    select: { id: true, source: true, content: true }
  })
  
  const reallyShort = allContent.filter(a => a.content && a.content.length < 500)
  
  console.log('\n--- Qualité Contenu ---')
  console.log(`Vides (0 chars)              : ${shortContent}`)
  console.log(`Courts (< 500 chars)         : ${reallyShort.length}`)
  
  if (reallyShort.length > 0) {
    console.log('  > Sources problématiques (Courts) :')
    const shortBySource: Record<string, number> = {}
    reallyShort.forEach(a => {
      const s = a.source || 'Inconnu'
      shortBySource[s] = (shortBySource[s] || 0) + 1
    })
    Object.entries(shortBySource).forEach(([src, count]) => {
      console.log(`    - ${src}: ${count}`)
    })
  }

  // 4. Images
  const noImage = await prisma.article.count({
    where: {
      publishedAt: { gte: start, lt: end },
      imageUrl: null,
      localImage: null
    }
  })
  console.log(`\nSans Image                   : ${noImage} (${((noImage/total)*100).toFixed(1)}%)`)

  // 5. Calendrier (Jours manquants ?)
  console.log('\n--- Distribution Journalière ---')
  const days = await prisma.article.groupBy({
    by: ['publishedAt'],
    where: { publishedAt: { gte: start, lt: end } },
  })
  
  // Aggregation manuelle par jour (YYYY-MM-DD)
  const dayCounts: Record<string, number> = {}
  days.forEach(d => {
    const dayStr = d.publishedAt.toISOString().split('T')[0]
    dayCounts[dayStr] = (dayCounts[dayStr] || 0) + 1
  })
  
  const sortedDays = Object.entries(dayCounts).sort((a, b) => a[0].localeCompare(b[0]))
  
  // Affichage compact
  let lowDays = 0
  sortedDays.forEach(([day, count]) => {
    if (count < 5) { // Seuil arbitraire de "peu d'activité"
      console.log(`⚠️  ${day} : ${count} articles (Faible)`)
      lowDays++
    }
  })
  
  if (lowDays === 0) console.log('✅ Activité régulière tout le mois.')
  console.log(`Moyenne : ~${Math.round(total / 30)} articles/jour`)

}

main().finally(() => prisma.$disconnect())
