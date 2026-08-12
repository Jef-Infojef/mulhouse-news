'use server'

import { convex } from '@/lib/prisma'
import { api } from '@/convex/_generated/api'
import type { Id } from '@/convex/_generated/dataModel'
import { headers } from 'next/headers'
import { revalidatePath } from 'next/cache'
import { createAdminSession, isAdminAuthenticated, safeEqual } from '@/lib/adminAuth'

// ─────────────────────────────────────────────────────────────────────────────
// Phase 2 : tous les accès données passent par les fonctions Convex
// (convex/app.ts) via ConvexHttpClient (lib/prisma.ts). Signatures exportées
// inchangées. Le retrait complet de Prisma du build se fera après la Phase 3
// (scripts GitHub Actions encore sur Prisma) : `prisma generate` reste dans le
// script build tant que phase 3 n'est pas faite.
// ─────────────────────────────────────────────────────────────────────────────

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
  try {
    // La logique du compteur (JSON {c,t}, fenêtre glissante, purge opportuniste)
    // vit dans la mutation Convex app:incRateLimit, qui renvoie le compteur à jour.
    const count = await convex.mutation(api.app.incRateLimit, {
      key,
      prefix: RL_PREFIX,
      max: MAX_ATTEMPTS,
      windowMs: ATTEMPT_WINDOW_MS,
    })
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
    await convex.mutation(api.app.deleteAppConfig, { key: RL_PREFIX + (await clientIp()) })
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

// Convex stocke les timestamps en epoch ms (number) ; le reste de l'app
// consomme des Date (JSON-LD, toLocaleString, date-fns). Conversion ici,
// comme le faisait Prisma (Date natifs).
const toDate = (value: number | null | undefined, fallback: number): Date =>
  new Date(typeof value === 'number' ? value : fallback)

const errorMessage = (error: unknown): string =>
  error instanceof Error ? error.message : String(error)

export async function getLatestArticles(query?: string) {
  try {
    const trimmed = query?.trim()
    const { articles } = await convex.query(api.app.getLatestArticles, trimmed ? { query: trimmed } : {})

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

    console.log(`${filteredArticles.length} articles uniques récupérés (sur ${mapped.length}).`)
    return { articles: filteredArticles, error: null }
  } catch (error: unknown) {
    console.error('ERREUR CONVEX:', error)
    return { articles: [], error: errorMessage(error) }
  }
}

export async function getArticleContent(id: string) {
  if (!(await isAdminAuthenticated())) return { content: null, error: 'Non autorisé' }
  try {
    // `id` est l'id Convex de l'article (celui renvoyé par getLatestArticles).
    const { content } = await convex.query(api.app.getArticleContent, { id: id as Id<'articles'> })
    return { content: content ?? null, error: null }
  } catch (error: unknown) {
    console.error('Erreur récupération contenu article:', error)
    return { content: null, error: errorMessage(error) }
  }
}

export async function getScrapingLogs() {
  if (!(await isAdminAuthenticated())) return { logs: [], error: 'Non autorisé' }
  try {
    const { logs } = await convex.query(api.app.getScrapingLogs, { limit: 100 })
    return {
      logs: (logs ?? []).map((log) => ({
        ...log,
        startedAt: new Date(log.startedAt),
        finishedAt: log.finishedAt ? new Date(log.finishedAt) : null,
      })),
      error: null,
    }
  } catch (error: unknown) {
    console.error('Erreur récupération logs:', error)
    return { logs: [], error: errorMessage(error) }
  }
}

export async function getAppConfig(key: string) {
  if (!(await isAdminAuthenticated())) return { value: null, error: 'Non autorisé' }
  try {
    const { value } = await convex.query(api.app.getAppConfig, { key })
    return { value: value ?? null, error: null }
  } catch (error: unknown) {
    return { value: null, error: errorMessage(error) }
  }
}

export async function updateAppConfig(key: string, value: string) {
  if (!(await isAdminAuthenticated())) return { success: false, error: 'Non autorisé' }
  try {
    await convex.mutation(api.app.setAppConfig, { key, value })
    return { success: true, error: null }
  } catch (error: unknown) {
    return { success: false, error: errorMessage(error) }
  }
}

export async function testEbraConnection(sessionValue: string, pooolValue?: string) {
  if (!(await isAdminAuthenticated())) return { success: false, message: 'Non autorisé' }
  try {
    // La logique réseau (fetch lalsace.fr + détection de marqueurs) vit dans
    // l'action Convex app:testEbraConnection.
    return await convex.action(api.app.testEbraConnection, pooolValue
      ? { session: sessionValue, poool: pooolValue }
      : { session: sessionValue })
  } catch (error: unknown) {
    console.error('[TEST EBRA] Erreur:', error)
    return { success: false, message: 'Erreur technique : ' + errorMessage(error) }
  }
}

export async function deleteArticle(id: string) {
  if (!(await isAdminAuthenticated())) return { success: false, error: 'Non autorisé' }
  try {
    await convex.mutation(api.app.deleteArticle, { id: id as Id<'articles'> })
    return { success: true, error: null }
  } catch (error: unknown) {
    console.error('Erreur suppression article:', error)
    return { success: false, error: errorMessage(error) }
  }
}
