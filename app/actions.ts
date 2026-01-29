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
    const clean = String(cookieValue).trim()
    let finalCookie = ''

    // Si l'utilisateur a collé un header Cookie complet, on l'utilise tel quel
    if (clean.includes('=') && clean.includes(';') && clean.length > 50) {
      finalCookie = clean
    } else {
      // Nettoyage agressif pour ne garder que la valeur hexadécimale
      let sessionValue = clean
      if (sessionValue.includes('ebra_session=')) sessionValue = sessionValue.split('ebra_session=')[1].split(';')[0]
      if (sessionValue.includes('.XCONNECT_SESSION=')) sessionValue = sessionValue.split('.XCONNECT_SESSION=')[1].split(';')[0]
      if (sessionValue.includes(':')) sessionValue = sessionValue.split(':')[1] 
      
      sessionValue = sessionValue.replace(/['"]/g, '').trim()
      
      // Si la valeur contient déjà "2=", on ne le rajoute pas
      const prefix = sessionValue.startsWith('2=') ? '' : '2='
      finalCookie = `.XCONNECT_SESSION=${prefix}${sessionValue}; .XCONNECTKeepAlive=2=1; .XCONNECT=2=1; _poool=9aab6ee3-fda6-43fc-a90e-29de3c73d8f7`
    }

    console.log(`[TEST EBRA] Tentative avec cookie: ${finalCookie.substring(0, 80)}...`)

    const homeResponse = await fetch('https://www.lalsace.fr/', {
      headers: {
        'Cookie': finalCookie,
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,application/apng,*/*;q=0.8',
        'Accept-Language': 'fr-FR,fr;q=0.9,en-US;q=0.8,en;q=0.7',
        'Cache-Control': 'no-store'
      }
    })

    const html = await homeResponse.text()
    
    // Debug dans les logs serveur
    console.log(`[TEST EBRA] Status: ${homeResponse.status}`)
    console.log(`[TEST EBRA] Taille HTML: ${html.length}`)
    
    const checks = {
      'Se déconnecter': html.includes('Se déconnecter'),
      'Mon compte': html.includes('Mon compte'),
      'Mon profil': html.includes('Mon profil'),
      'subscriber': html.includes('subscriber'),
      'Abonné': html.includes('Abonné'),
      'premium': html.includes('premium'),
      'pro-item': html.includes('pro-item'),
      'AccountCircle': html.includes('AccountCircle'),
      'connected': html.includes('connected'),
      'logged-in': html.includes('logged-in'),
      'auth': html.includes('auth'),
    }
    console.log('[TEST EBRA] Résultats détection:', checks)
    
    // Détection plus large
    const isConnected = Object.values(checks).some(v => v === true)

    if (!isConnected) {
      if (html.includes('Ray ID:') || html.includes('cloudflare')) {
        return { success: false, message: 'Bloqué par Cloudflare (le serveur ne peut pas simuler le navigateur)' }
      }
      return { success: false, message: 'Session non reconnue. Vérifiez que vous avez bien copié la valeur de ebra_session.' }
    }

    // Test sur un article pour confirmer l'accès
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
          'Cookie': finalCookie,
          'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
      })
      const artHtml = await artResponse.text()
      const hasContent = artHtml.includes('textComponent') || artHtml.includes('article__body') || artHtml.length > 60000
      
      if (hasContent) {
        return { success: true, message: 'Succès ! Vous êtes bien connecté en Premium.' }
      } else {
        return { success: true, message: 'Connecté, mais le contenu de l\'article semble quand même limité.' }
      }
    }

    return { success: true, message: 'Connecté avec succès !' }
  } catch (error: any) {
    console.error('[TEST EBRA] Erreur:', error)
    return { success: false, message: 'Erreur technique : ' + error.message }
  }
}

