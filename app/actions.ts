'use server'

import prisma from '@/lib/prisma'

export async function getLatestArticles(query?: string) {
  try {
    const whereClause = query ? {
      OR: [
        { title: { contains: query, mode: 'insensitive' as const } },
        { description: { contains: query, mode: 'insensitive' as const } },
        { source: { contains: query, mode: 'insensitive' as const } },
      ],
    } : {};

    const articles = await prisma.article.findMany({
      where: whereClause,
      take: 200, 
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

export async function getScrapingLogs() {
  try {
    const logs = await prisma.scrapingLog.findMany({
      orderBy: {
        startedAt: 'desc',
      },
      take: 100,
    })
    return { logs, error: null }
  } catch (error: any) {
    console.error('Erreur récupération logs:', error)
    return { logs: [], error: error.message || String(error) }
  }
}
