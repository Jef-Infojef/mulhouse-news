'use server'

import {
  fetchAivenLatestArticles,
  fetchAivenArticleContent,
  setAivenArticleHidden,
} from '@/lib/aiven-news'
import {
  getConfigValue,
  setConfigValue,
  deleteConfigValue,
  incrementRateLimit,
  fetchScrapingLogs,
} from '@/lib/site-db'
import { headers } from 'next/headers'
import { revalidatePath } from 'next/cache'
import { createAdminSession, isAdminAuthenticated, safeEqual } from '@/lib/adminAuth'

// ─────────────────────────────────────────────────────────────────────────────
// Accès 100 % PostgreSQL direct sur le serveur Hostinger VPS (rag_db)
// ─────────────────────────────────────────────────────────────────────────────

const MAX_ATTEMPTS = 10
const ATTEMPT_WINDOW_MS = 15 * 60 * 1000
const RL_PREFIX = 'ratelimit:login:'

async function clientIp(): Promise<string> {
  const headerStore = await headers()
  return headerStore.get('x-forwarded-for')?.split(',')[0]?.trim() || 'unknown'
}

async function isRateLimited(): Promise<boolean> {
  const key = RL_PREFIX + (await clientIp())
  try {
    const count = await incrementRateLimit(key, RL_PREFIX, ATTEMPT_WINDOW_MS)
    return count > MAX_ATTEMPTS
  } catch (error) {
    console.error('[LOGIN] Rate limit indisponible, tentative refusée:', error)
    return true
  }
}

async function clearRateLimit(): Promise<void> {
  try {
    await deleteConfigValue(RL_PREFIX + (await clientIp()))
  } catch {
    // Rien à nettoyer
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

const toDate = (value: number | null | undefined, fallback: number): Date =>
  new Date(typeof value === 'number' ? value : fallback)

const errorMessage = (error: unknown): string =>
  error instanceof Error ? error.message : String(error)

export async function getLatestArticles(query?: string) {
  try {
    const trimmed = query?.trim()
    const articles = await fetchAivenLatestArticles(trimmed)

    const mapped = (articles ?? []).map((article) => ({
      ...article,
      id: article.id,
      publishedAt: new Date(article.publishedAt),
      scrapedAt: toDate(article.scrapedAt, article.publishedAt),
      createdAt: toDate(article.createdAt, article.publishedAt),
      updatedAt: toDate(article.updatedAt, article.publishedAt),
    }))

    // --- FILTRAGE DES DOUBLONS AVANCÉ ---
    const seenImageUuids = new Set<string>()
    const seenTitles = new Set<string>()
    const seenImageUrls = new Set<string>()

    const filteredArticles = mapped.filter((article) => {
      // 1. Filtrage par Titre (nettoyé et minuscule)
      const cleanTitle = article.title.trim().toLowerCase()
      if (seenTitles.has(cleanTitle)) {
        return false
      }

      // 2. Filtrage par URL d'image identique (si présente)
      if (article.imageUrl) {
        if (seenImageUrls.has(article.imageUrl)) {
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
            return false
          }
          seenImageUuids.add(uuid)
        }
      }

      // Marquer comme vu
      seenTitles.add(cleanTitle)
      return true
    })

    return { articles: filteredArticles, error: null }
  } catch (error: unknown) {
    console.error('ERREUR DB HOSTINGER:', error)
    return { articles: [], error: errorMessage(error) }
  }
}

export async function getArticleContent(id: string) {
  if (!(await isAdminAuthenticated())) return { content: null, error: 'Non autorisé' }
  try {
    const content = await fetchAivenArticleContent(id)
    return { content, error: null }
  } catch (error: unknown) {
    console.error('Erreur récupération contenu article:', error)
    return { content: null, error: errorMessage(error) }
  }
}

export async function getScrapingLogs() {
  if (!(await isAdminAuthenticated())) return { logs: [], error: 'Non autorisé' }
  try {
    const logs = await fetchScrapingLogs(100)
    return { logs, error: null }
  } catch (error: unknown) {
    console.error('Erreur récupération logs:', error)
    return { logs: [], error: errorMessage(error) }
  }
}

export async function getAppConfig(key: string) {
  if (!(await isAdminAuthenticated())) return { value: null, error: 'Non autorisé' }
  try {
    return { value: await getConfigValue(key), error: null }
  } catch (error: unknown) {
    return { value: null, error: errorMessage(error) }
  }
}

export async function updateAppConfig(key: string, value: string) {
  if (!(await isAdminAuthenticated())) return { success: false, error: 'Non autorisé' }
  try {
    await setConfigValue(key, value)
    return { success: true, error: null }
  } catch (error: unknown) {
    return { success: false, error: errorMessage(error) }
  }
}

export async function testEbraConnection(sessionValue: string, pooolValue?: string) {
  if (!(await isAdminAuthenticated())) return { success: false, message: 'Non autorisé' }
  try {
    const cleanSession = String(sessionValue).trim()
    const cleanPoool = pooolValue
      ? String(pooolValue).trim()
      : '9aab6ee3-fda6-43fc-a90e-29de3c73d8f7'

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
    const uuidMatch = finalPoool.match(
      /[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}/
    )
    if (uuidMatch) finalPoool = uuidMatch[0]
    finalPoool = finalPoool.replace(/['"]/g, '').trim()

    const finalCookie = `.XCONNECT_SESSION=${finalSession}; .XCONNECTKeepAlive=2=1; .XCONNECT=2=1; _poool=${finalPoool}`

    const homeResponse = await fetch('https://www.lalsace.fr/', {
      headers: {
        Cookie: finalCookie,
        'User-Agent':
          'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        Accept:
          'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,application/apng,*/*;q=0.8',
        'Accept-Language': 'fr-FR,fr;q=0.9,en-US;q=0.8,en;q=0.7',
        'Cache-Control': 'no-store',
      },
    })

    const html = await homeResponse.text()
    const checks = {
      'Se déconnecter': html.includes('Se déconnecter'),
      'Mon compte': html.includes('Mon compte'),
      'Mon profil': html.includes('Mon profil'),
      subscriber: html.includes('subscriber'),
      Abonné: html.includes('Abonné'),
      premium: html.includes('premium'),
      'pro-item': html.includes('pro-item'),
      AccountCircle: html.includes('AccountCircle'),
      connected: html.includes('connected'),
      'logged-in': html.includes('logged-in'),
      auth: html.includes('auth'),
      XCONNECT: html.includes('XCONNECT'),
      JSESSIONID: html.includes('JSESSIONID'),
      'user-menu': html.includes('user-menu'),
      'mon-espace': html.includes('mon-espace'),
      'espace-client': html.includes('espace-client'),
    }

    const isConnected = Object.values(checks).some((value) => value === true)
    if (isConnected || html.length > 300000) {
      return { success: true, message: 'Connexion EBRA valide (session active)' }
    } else {
      if (html.includes('Ray ID:') || html.includes('cloudflare')) {
        return { success: false, message: 'Bloqué par Cloudflare' }
      }
      return { success: false, message: 'Session invalide ou expirée' }
    }
  } catch (error: unknown) {
    console.error('[TEST EBRA] Erreur:', error)
    return { success: false, message: 'Erreur technique : ' + errorMessage(error) }
  }
}

export async function deleteArticle(id: string) {
  if (!(await isAdminAuthenticated())) return { success: false, error: 'Non autorisé' }
  try {
    const ok = await setAivenArticleHidden(id, true)
    return ok
      ? { success: true, error: null }
      : { success: false, error: 'Article introuvable' }
  } catch (error: unknown) {
    console.error('Erreur suppression article:', error)
    return { success: false, error: errorMessage(error) }
  }
}
