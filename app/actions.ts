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

export async function getAppConfig(key: string) {
  try {
    const config = await prisma.appConfig.findUnique({
      where: { key }
    })
    return { value: config?.value || null, error: null }
  } catch (error: any) {
    return { value: null, error: error.message }
  }
}

export async function updateAppConfig(key: string, value: string) {
  try {
    await prisma.appConfig.upsert({
      where: { key },
      update: { value },
      create: { key, value }
    })
    return { success: true, error: null }
  } catch (error: any) {
    return { success: false, error: error.message }
  }
}

export async function testEbraConnection(cookieValue: string) {
  try {
    const clean = cookieValue.strip ? cookieValue.trim() : String(cookieValue).trim()
    const sessionCookie = clean.includes('ebra_session=') 
      ? clean.split('ebra_session=')[1].split(';')[0] 
      : clean.replace(/['"]/g, '')

    // 1. Test de connexion simple sur la home
    const homeResponse = await fetch('https://www.lalsace.fr/', {
      headers: {
        'Cookie': `.XCONNECT_SESSION=${sessionCookie}; .XCONNECTKeepAlive=2=1; .XCONNECT=2=1`,
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36'
      },
      cache: 'no-store'
    })

    const html = await homeResponse.text()
    const isConnected = html.includes('Se déconnecter') || html.includes('Mon compte') || html.includes('Mon profil')

    if (!isConnected) {
      return { success: false, message: 'Session invalide ou expirée (non reconnu par le site)' }
    }

    // 2. Test sur un article premium (on cherche un lien récent en base ou on en prend un connu)
    const lastPremium = await prisma.article.findFirst({
      where: {
        source: { contains: 'Alsace', mode: 'insensitive' },
        link: { contains: 'lalsace.fr' }
      },
      orderBy: { publishedAt: 'desc' }
    })

    if (lastPremium) {
      const artResponse = await fetch(lastPremium.link, {
        headers: {
          'Cookie': `.XCONNECT_SESSION=${sessionCookie}; .XCONNECTKeepAlive=2=1; .XCONNECT=2=1`,
          'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36'
        },
        cache: 'no-store'
      })
      const artHtml = await artResponse.text()
      const hasContent = artHtml.includes('textComponent') || artHtml.length > 50000 // Un article complet est lourd
      
      if (hasContent) {
        return { success: true, message: 'Connexion Premium validée ! Accès au contenu complet confirmé.' }
      } else {
        return { success: true, message: 'Connecté, mais le contenu complet semble bloqué ou protégé.' }
      }
    }

    return { success: true, message: 'Connecté avec succès (aucun article récent pour test complet).' }
  } catch (error: any) {
    return { success: false, message: 'Erreur technique : ' + error.message }
  }
}

