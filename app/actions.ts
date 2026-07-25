'use server'

import prisma from '@/lib/prisma'
import { headers } from 'next/headers'
import { revalidatePath } from 'next/cache'
import { createAdminSession, isAdminAuthenticated, safeEqual } from '@/lib/adminAuth'

// Limitation des essais de connexion. Le compteur vit en base (table AppConfig,
// simple clé/valeur : aucune migration requise) et non en mémoire : sur Vercel,
// chaque instance serverless a son propre tas et disparaît au cold start, donc un
// compteur en mémoire ne limitait rien en pratique.
const MAX_ATTEMPTS = 10
const ATTEMPT_WINDOW_MS = 15 * 60 * 1000
const RL_PREFIX = 'ratelimit:login:'

async function clientIp(): Promise<string> {
  const headerStore = await headers()
  return headerStore.get('x-forwarded-for')?.split(',')[0]?.trim() || 'unknown'
}

async function isRateLimited(): Promise<boolean> {
  const key = RL_PREFIX + (await clientIp())
  const now = Date.now()
  try {
    const existing = await prisma.appConfig.findUnique({ where: { key } })
    let count = 0
    let windowStart = now
    if (existing) {
      const parsed = JSON.parse(existing.value) as { c?: number; t?: number }
      if (typeof parsed.t === 'number' && now - parsed.t <= ATTEMPT_WINDOW_MS) {
        count = typeof parsed.c === 'number' ? parsed.c : 0
        windowStart = parsed.t
      }
    }
    count++
    const value = JSON.stringify({ c: count, t: windowStart })
    await prisma.appConfig.upsert({
      where: { key },
      update: { value },
      create: { key, value },
    })
    // Purge opportuniste des compteurs expirés, pour éviter que la table n'enfle
    // si quelqu'un pulvérise des tentatives depuis de nombreuses IP.
    if (Math.random() < 0.02) {
      await prisma.appConfig.deleteMany({
        where: {
          key: { startsWith: RL_PREFIX },
          updatedAt: { lt: new Date(now - ATTEMPT_WINDOW_MS) },
        },
      })
    }
    return count > MAX_ATTEMPTS
  } catch (error) {
    // En cas d'indisponibilité de la base, on refuse la tentative plutôt que de
    // laisser passer un bruteforce non compté. L'admin dépend de toute façon de la
    // base pour tout le reste, il n'y a donc rien à perdre à échouer ici.
    console.error('[LOGIN] Rate limit indisponible, tentative refusée:', error)
    return true
  }
}

async function clearRateLimit(): Promise<void> {
  try {
    await prisma.appConfig.delete({ where: { key: RL_PREFIX + (await clientIp()) } })
  } catch {
    // Rien à nettoyer (ou base indisponible) : sans conséquence.
  }
}

export async function verifyAdminPassword(password: string) {
  if (await isRateLimited()) {
    return { success: false, error: 'Trop de tentatives, réessayez plus tard.' }
  }
  const correct = process.env.ADMIN_PASSWORD?.trim()
  if (!correct || !safeEqual(password.trim(), correct)) return { success: false }
  const created = await createAdminSession()
  if (created) await clearRateLimit()
  return { success: created }
}

export async function checkAdminAuth() {
  return isAdminAuthenticated()
}

export async function revalidateSite() {
  if (!(await isAdminAuthenticated())) return { success: false }
  revalidatePath('/')
  return { success: true }
}

export async function getLatestArticles(query?: string) {
  try {
    // La recherche ne porte pas sur `content` : ce champ contient le texte intégral
    // scrapé (dont des articles derrière paywall), et un filtre `contains` public
    // permettrait de le reconstituer sous-chaîne par sous-chaîne sans jamais le renvoyer.
    const whereClause = query ? {
      hidden: false,
      OR: [
        { title: { contains: query, mode: 'insensitive' as const } },
        { description: { contains: query, mode: 'insensitive' as const } },
        { source: { contains: query, mode: 'insensitive' as const } },
      ],
    } : { hidden: false };

    // `content` (texte intégral scrapé) est volontairement exclu : il alourdirait
    // le payload de plusieurs Mo. L'admin le charge à la demande via getArticleContent().
    const articles = await prisma.article.findMany({
      where: whereClause,
      take: 200,
      orderBy: {
        publishedAt: 'desc',
      },
      select: {
        id: true,
        title: true,
        link: true,
        imageUrl: true,
        imageCaption: true,
        source: true,
        description: true,
        publishedAt: true,
        scrapedAt: true,
        createdAt: true,
        updatedAt: true,
        localImage: true,
        r2Url: true,
        hidden: true,
        ArticleGoogleTag: {
          include: {
            NewsTag: true,
          },
        },
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

export async function getArticleContent(id: string) {
  if (!(await isAdminAuthenticated())) return { content: null, error: 'Non autorisé' }
  try {
    const article = await prisma.article.findUnique({
      where: { id },
      select: { content: true },
    })
    return { content: article?.content ?? null, error: null }
  } catch (error: any) {
    console.error('Erreur récupération contenu article:', error)
    return { content: null, error: error.message || String(error) }
  }
}

export async function getScrapingLogs() {
  if (!(await isAdminAuthenticated())) return { logs: [], error: 'Non autorisé' }
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
  if (!(await isAdminAuthenticated())) return { value: null, error: 'Non autorisé' }
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
  if (!(await isAdminAuthenticated())) return { success: false, error: 'Non autorisé' }
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

export async function testEbraConnection(sessionValue: string, pooolValue?: string) {
  if (!(await isAdminAuthenticated())) return { success: false, message: 'Non autorisé' }
  try {
    const cleanSession = String(sessionValue).trim()
    const cleanPoool = pooolValue ? String(pooolValue).trim() : '9aab6ee3-fda6-43fc-a90e-29de3c73d8f7'
    
    let finalSession = cleanSession
    if (cleanSession.includes('2=')) {
      finalSession = cleanSession.substring(cleanSession.indexOf('2='))
      if (finalSession.includes(';')) finalSession = finalSession.split(';')[0]
    }
    finalSession = finalSession.replace(/['"]/g, '').trim()

    let finalPoool = cleanPoool
    if (cleanPoool.includes('_poool=')) {
      finalPoool = cleanPoool.split('_poool=')[1].split(';')[0]
    }
    // Formats DevTools type '_poool :"79f0c712-..."' : on extrait l'UUID directement
    const uuidMatch = finalPoool.match(/[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}/)
    if (uuidMatch) finalPoool = uuidMatch[0]
    finalPoool = finalPoool.replace(/['"]/g, '').trim()

    const finalCookie = `.XCONNECT_SESSION=${finalSession}; .XCONNECTKeepAlive=2=1; .XCONNECT=2=1; _poool=${finalPoool}`

    console.log(`[TEST EBRA] Cookie final: ${finalCookie.substring(0, 80)}...`)

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
      'XCONNECT': html.includes('XCONNECT'),
      'JSESSIONID': html.includes('JSESSIONID'),
      'user-menu': html.includes('user-menu'),
      'mon-espace': html.includes('mon-espace'),
      'espace-client': html.includes('espace-client'),
    }
    console.log('[TEST EBRA] Résultats détection:', checks)
    
    // Détection plus large
    const isConnected = Object.values(checks).some(v => v === true)
    
    // Si tous les tests échouent mais qu'on a un gros HTML (comme vu dans les logs ~840ko), 
    // on considère que la session est probablement active car le paywall réduit drastiquement la taille.
    if (!isConnected && html.length > 300000) {
      console.log(`[TEST EBRA] Aucune clé explicite trouvée mais HTML volumineux (${html.length}), passage au test d'article.`)
      // On continue pour voir si l'article est complet
    } else if (!isConnected) {
      if (html.includes('Ray ID:') || html.includes('cloudflare')) {
        return { success: false, message: 'Bloqué par Cloudflare (le serveur ne peut pas simuler le navigateur)' }
      }
      return { success: false, message: 'Session non reconnue sur la home. Vérifiez la valeur du cookie.' }
    }

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

export async function deleteArticle(id: string) {
  if (!(await isAdminAuthenticated())) return { success: false, error: 'Non autorisé' }
  try {
    await prisma.article.delete({
      where: { id }
    })
    return { success: true, error: null }
  } catch (error: any) {
    console.error('Erreur suppression article:', error)
    return { success: false, error: error.message || String(error) }
  }
}

