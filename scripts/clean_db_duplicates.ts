import { PrismaClient } from '@prisma/client'
const prisma = new PrismaClient()

async function main() {
  console.log("Recherche des doublons dans la base de données...")
  
  // On récupère tous les articles récents (on limite aux 1000 derniers pour la performance, 
  // car les doublons sont généralement proches dans le temps)
  const articles = await prisma.article.findMany({
    take: 1000,
    orderBy: { createdAt: 'desc' }
  })

  const seenTitles = new Map<string, string>() // title.toLowerCase() -> id
  const seenImageUrls = new Map<string, string>() // imageUrl -> id
  const seenImageUuids = new Map<string, string>() // uuid -> id
  const toDelete = new Set<string>()

  for (const article of articles) {
    const cleanTitle = article.title.trim().toLowerCase()
    const imageUrl = article.imageUrl
    let ebraUuid = null
    
    if (imageUrl) {
      const match = imageUrl.match(/\/images\/([^\/]+)\//)
      if (match) ebraUuid = match[1]
    }

    let isDuplicate = false
    let reason = ""

    // Vérification Titre
    if (seenTitles.has(cleanTitle)) {
      isDuplicate = true
      reason = `Titre identique à ${seenTitles.get(cleanTitle)}`
    } 
    // Vérification Image URL
    else if (imageUrl && seenImageUrls.has(imageUrl)) {
      isDuplicate = true
      reason = `Image URL identique à ${seenImageUrls.get(imageUrl)}`
    }
    // Vérification UUID EBRA
    else if (ebraUuid && seenImageUuids.has(ebraUuid)) {
      isDuplicate = true
      reason = `UUID Image EBRA identique à ${seenImageUuids.get(ebraUuid)}`
    }

    if (isDuplicate) {
      toDelete.add(article.id)
      console.log(`[DOUBLON] Supprimer: "${article.title}" (${article.source}) - Raison: ${reason}`)
    } else {
      // Si ce n'est pas un doublon, on enregistre ses caractéristiques pour les suivants
      seenTitles.set(cleanTitle, article.id)
      if (imageUrl) seenImageUrls.set(imageUrl, article.id)
      if (ebraUuid) seenImageUuids.set(ebraUuid, article.id)
    }
  }

  if (toDelete.size > 0) {
    console.log(`\nSuppression de ${toDelete.size} articles...`)
    const result = await prisma.article.deleteMany({
      where: {
        id: { in: Array.from(toDelete) }
      }
    })
    console.log(`Terminé. ${result.count} articles supprimés avec succès.`)
  } else {
    console.log("\nAucun doublon trouvé dans les 1000 derniers articles.")
  }
}

main()
  .catch(console.error)
  .finally(() => prisma.$disconnect())
