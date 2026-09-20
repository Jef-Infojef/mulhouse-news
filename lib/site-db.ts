import { Pool } from "pg"

/**
 * Accès SQL à la base Supabase principale, pour ce que l'admin lisait dans Convex.
 *
 * `AppConfig` (4 clés : cookie EBRA, cooldowns de retry, cache du fil d'Ariane)
 * et `ScrapingLog` (1 534 entrées) vivent ici depuis toujours : Convex n'en
 * était qu'une copie, écrite pendant la migration. Son déploiement coupé le
 * 11/09/2026, l'admin est devenue inaccessible — non pas faute de données, mais
 * parce que le compteur d'essais de connexion, qui refuse par sécurité quand sa
 * base ne répond pas, ferme le portillon à chaque tentative.
 *
 * Rien à migrer donc : il s'agit de lire là où la donnée se trouve.
 */

const globalForSite = globalThis as unknown as { sitePool: Pool | undefined }

function resolveSsl(url: string) {
  if (
    url.includes("sslmode=require") ||
    url.includes("sslmode=verify") ||
    url.includes("supabase.co") ||
    url.includes("aivencloud.com") ||
    url.includes("pooler.supabase.com")
  ) {
    if (url.includes("sslmode=disable")) return false
    return { rejectUnauthorized: false }
  }
  return false
}

export function getSitePool(): Pool {
  if (!globalForSite.sitePool) {
    const url = process.env.DATABASE_URL?.trim()
    if (!url) throw new Error("DATABASE_URL manquant (base Supabase principale)")
    globalForSite.sitePool = new Pool({
      // `pgbouncer=true` est un paramètre Prisma : libpq le refuse.
      connectionString: url.replace(/[?&]pgbouncer=true/, ""),
      ssl: resolveSsl(url),
      max: 5,
      idleTimeoutMillis: 30000,
      connectionTimeoutMillis: 15000,
      statement_timeout: 15000,
      allowExitOnIdle: true,
    })
    globalForSite.sitePool.on("error", (err) => console.error("[site-db] pool:", err))
  }
  return globalForSite.sitePool
}

export async function getConfigValue(key: string): Promise<string | null> {
  const { rows } = await getSitePool().query(`SELECT value FROM "AppConfig" WHERE key = $1`, [key])
  return rows[0]?.value ?? null
}

export async function setConfigValue(key: string, value: string): Promise<void> {
  await getSitePool().query(
    `INSERT INTO "AppConfig" (key, value, "updatedAt") VALUES ($1, $2, now())
     ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value, "updatedAt" = now()`,
    [key, value]
  )
}

export async function deleteConfigValue(key: string): Promise<void> {
  await getSitePool().query(`DELETE FROM "AppConfig" WHERE key = $1`, [key])
}

/**
 * Compteur d'essais de connexion, fenêtre glissante.
 *
 * Même logique que la mutation Convex `app:incRateLimit` : un JSON `{c, t}` par
 * IP, remis à zéro quand la fenêtre est dépassée, et purge opportuniste des
 * compteurs périmés pour que la table ne grossisse pas indéfiniment.
 *
 * Le compteur vit en base et non en mémoire : sur Vercel chaque instance
 * serverless a son propre tas et disparaît au cold start.
 */
export async function incrementRateLimit(
  key: string,
  prefix: string,
  windowMs: number
): Promise<number> {
  const pool = getSitePool()
  const maintenant = Date.now()

  const { rows } = await pool.query(`SELECT value FROM "AppConfig" WHERE key = $1`, [key])
  let compteur = 0
  let debut = maintenant
  if (rows[0]?.value) {
    try {
      const { c, t } = JSON.parse(rows[0].value) as { c?: number; t?: number }
      if (typeof t === "number" && maintenant - t < windowMs) {
        compteur = typeof c === "number" ? c : 0
        debut = t
      }
    } catch {
      // Valeur illisible : on repart d'un compteur neuf plutôt que de bloquer.
    }
  }
  compteur += 1

  await pool.query(
    `INSERT INTO "AppConfig" (key, value, "updatedAt") VALUES ($1, $2, now())
     ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value, "updatedAt" = now()`,
    [key, JSON.stringify({ c: compteur, t: debut })]
  )

  // Purge opportuniste : les compteurs d'autres IP dont la fenêtre est passée.
  //
  // Le seuil est calculé par le SERVEUR. `AppConfig.updatedAt` est un
  // `timestamp` SANS fuseau (convention Prisma) : lui comparer une date JS
  // décale la limite de l'offset local — +2 h en septembre — donc le seuil
  // tombait dans le futur et la purge effaçait le compteur qu'on venait
  // d'écrire, laissant le compteur bloqué à 1 et le bruteforce non compté.
  await pool
    .query(
      `DELETE FROM "AppConfig"
        WHERE key LIKE $1 AND key <> $2
          AND "updatedAt" < now() - make_interval(secs => $3)`,
      [`${prefix}%`, key, windowMs / 1000]
    )
    .catch(() => undefined)

  return compteur
}

export interface ScrapingLogRow {
  id: string
  startedAt: Date
  finishedAt: Date | null
  status: string
  isConnected: boolean
  articlesCount: number
  successCount: number
  errorCount: number
  details: unknown
  errorMessage: string | null
}

export async function fetchScrapingLogs(limit = 100): Promise<ScrapingLogRow[]> {
  const { rows } = await getSitePool().query(
    `SELECT id, "startedAt", "finishedAt", status, "isConnected",
            "articlesCount", "successCount", "errorCount", details, "errorMessage"
       FROM "ScrapingLog"
      ORDER BY "startedAt" DESC
      LIMIT $1`,
    [limit]
  )
  return rows as ScrapingLogRow[]
}
