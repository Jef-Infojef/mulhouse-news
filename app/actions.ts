'use server'

import prisma from '@/lib/prisma'

export async function getLatestArticles() {
  try {
    const articles = await prisma.article.findMany({
      take: 200, // Optimisation : on ne récupère que les 200 derniers
      orderBy: {
        publishedAt: 'desc',
      },
    })

    // --- FILTRAGE DES DOUBLONS DNA/ALSACE PAR UUID IMAGE ---
    const seenImageUuids = new Set<string>()
    const filteredArticles = articles.filter(article => {
      if (!article.imageUrl) return true // On garde si pas d'image

      // Extraction de l'UUID image EBRA (ex: /images/XXXX-YYYY-ZZZZ/)
      const match = article.imageUrl.match(/\/images\/([^\/]+)\//)
      if (match) {
        const uuid = match[1]
        
        // Si c'est du DNA et qu'on a déjà vu cet UUID (donc chez L'Alsace car trié par date/priorité)
        if (article.source?.toLowerCase().includes('dna') && seenImageUuids.has(uuid)) {
          console.log(`Filtrage doublon DNA ignoré: ${article.title}`)
          return false
        }
        
        seenImageUuids.add(uuid)
      }
      return true
    })

    console.log(`${filteredArticles.length} articles uniques récupérés (sur ${articles.length}).`)
    return { articles: filteredArticles, error: null }
  } catch (error: any) {
    console.error('ERREUR PRISMA:', error)
    return { articles: [], error: error.message || String(error) }
  }
}
