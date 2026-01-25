'use server'

import prisma from '@/lib/prisma'

export async function getLatestArticles(query?: string) {
  try {
    const whereClause = query ? {
      OR: [
        { title: { contains: query, mode: 'insensitive' as const } }, { content: { contains: query, mode: 'insensitive' as const } },
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

    // --- FILTRAGE DES DOUBLONS AVANCÉ ---
    const seenImageUuids = new Set<string>()
    const seenTitles = new Set<string>()
    const seenImageUrls = new Set<string>()

    const filteredArticles = articles.filter(article => {
      // 1. Filtrage par Titre (nettoyé et minuscule)
      const cleanTitle = article.title.trim().toLowerCase()
      if (seenTitles.has(cleanTitle)) {
        console.log(`Filtrage doublon TITRE ignoré: ${article.title}`)
        return false
      }

      // 2. Filtrage par URL d'image identique (si présente)
      if (article.imageUrl) {
        if (seenImageUrls.has(article.imageUrl)) {
          console.log(`Filtrage doublon IMAGE_URL ignoré: ${article.title}`)
          return false
        }
        seenImageUrls.add(article.imageUrl)
      }

      // 3. Filtrage par UUID image EBRA (L'Alsace, DNA, Est Républicain, Vosges Matin, etc.)
      if (article.imageUrl) {
        const match = article.imageUrl.match(/\/images\/([^\/]+)\//)
        if (match) {
          const uuid = match[1]
          if (seenImageUuids.has(uuid)) {
            console.log(`Filtrage doublon UUID EBRA ignoré: ${article.title}`)
            return false
          }
          seenImageUuids.add(uuid)
        }
      }

      // Marquer comme vu
      seenTitles.add(cleanTitle)
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

