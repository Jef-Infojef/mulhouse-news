import { PrismaClient } from '@prisma/client'
const prisma = new PrismaClient()

async function main() {
  console.log("Extraction des 10 derniers logs de scraping...\n")
  const logs = await prisma.scrapingLog.findMany({
    take: 10,
    orderBy: { startedAt: 'desc' }
  })

  if (logs.length === 0) {
    console.log("Aucun log trouvé dans la table ScrapingLog.")
    return
  }

  logs.forEach(log => {
    const duration = log.finishedAt 
      ? Math.round((new Date(log.finishedAt).getTime() - new Date(log.startedAt).getTime()) / 1000) + "s"
      : "En cours ou interrompu"
    
    console.log(`[${log.startedAt.toLocaleString('fr-FR')}] Status: ${log.status}`)
    console.log(`   Articles: ${log.articlesCount} | Succès: ${log.successCount} | Erreurs: ${log.errorCount}`)
    console.log(`   Durée: ${duration} | Connecté: ${log.isConnected ? 'Oui' : 'Non'}`)
    if (log.errorMessage) console.log(`   Erreur: ${log.errorMessage}`)
    console.log('---')
  })
}

main().finally(() => prisma.$disconnect())
