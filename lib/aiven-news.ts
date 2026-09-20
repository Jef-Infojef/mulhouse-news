import { Pool } from "pg"

/**
 * Lecture des articles de presse dans la base RAG (Aiven).
 *
 * Cette application lisait Convex. Déploiement coupé le 11/09/2026 pour
 * dépassement de quota, elle affiche « Aucun article trouvé » alors que la
 * collecte, elle, n'a jamais cessé.
 *
 * Depuis le 13/09/2026 les scrapers consignent chaque article dans un journal
 * que `rag_sync_articles.py --journal` écrit directement sur l'Aiven (tables
 * `Article`, `ArticleImage`, `ArticleTag`, `NewsTag`). Cette base est donc la
 * seule à rester à jour quoi qu'il arrive à Convex.
 *
 * Le format rendu reproduit exactement celui de `convex/app.ts:getLatestArticles`
 * — `ArticleGoogleTag: [{ NewsTag }]` compris — pour que le front n'ait rien à
 * savoir de la bascule.
 *
 * Sans RAG_DATABASE_URL, `hasAivenNews()` est faux et l'application garde son
 * comportement actuel.
 */

const globalForAiven = globalThis as unknown as { aivenNewsPool: Pool | undefined }

/** Nom sans préfixe `use` : la règle react-hooks prendrait `useXxx` pour un hook. */
export function hasAivenNews(): boolean {
  return Boolean(process.env.RAG_DATABASE_URL?.trim())
}

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

function getPool(): Pool {
  if (!globalForAiven.aivenNewsPool) {
    const url = process.env.RAG_DATABASE_URL || ""
    globalForAiven.aivenNewsPool = new Pool({
      connectionString: url,
      ssl: resolveSsl(url),
      max: 5,
      idleTimeoutMillis: 30000,
      connectionTimeoutMillis: 15000,
      statement_timeout: 15000,
      allowExitOnIdle: true,
    })
    globalForAiven.aivenNewsPool.on("error", (err) => console.error("[aiven-news] pool:", err))
  }
  return globalForAiven.aivenNewsPool
}

/** Même plafond que LIST_LIMIT côté Convex. */
const LIST_LIMIT = 200

export interface AivenListedArticle {
  id: string
  title: string
  link: string
  imageUrl: string | null
  imageCaption: string | null
  source: string | null
  description: string | null
  publishedAt: number
  scrapedAt: number | null
  createdAt: number | null
  updatedAt: number | null
  localImage: string | null
  r2Url: string | null
  author: string | null
  category: string | null
  hidden: boolean
  ArticleGoogleTag: Array<{
    NewsTag: { id: string; name: string; slug: string; color: string | null }
  }>
}

function ms(valeur: unknown): number | null {
  if (!valeur) return null
  const d = valeur instanceof Date ? valeur : new Date(String(valeur))
  return Number.isNaN(d.getTime()) ? null : d.getTime()
}

/**
 * Les 200 derniers articles publiés, ou ceux qui correspondent à la recherche.
 *
 * La recherche porte sur titre, résumé et source, comme les trois index de
 * recherche Convex — pas sur le corps, qui n'est pas indexé ici.
 */
export async function fetchAivenLatestArticles(query?: string): Promise<AivenListedArticle[]> {
  const pool = getPool()
  const motif = query?.trim() ? `%${query.trim()}%` : null
  const filtre = motif
    ? `hidden = false AND (title ILIKE $1 OR description ILIKE $1 OR source ILIKE $1)`
    : `hidden = false`
  const params: unknown[] = motif ? [motif] : []

  const { rows } = await pool.query(
    `SELECT id, title, link, "imageUrl", "imageCaption", source, description,
            "publishedAt", "scrapedAt", "createdAt", "updatedAt",
            "localImage", "r2Url", author, category, hidden
       FROM "Article"
      WHERE ${filtre}
      ORDER BY "publishedAt" DESC NULLS LAST
      LIMIT $${params.length + 1}`,
    [...params, LIST_LIMIT]
  )
  if (!rows.length) return []

  // Tags en une requête pour toute la page : un aller-retour par article
  // coûterait 200 requêtes à chaque chargement.
  const { rows: liens } = await pool.query(
    `SELECT at."articleId", t.id, t.name, t.slug, t.color
       FROM "ArticleTag" at
       JOIN "NewsTag" t ON t.id = at."tagId"
      WHERE at."articleId" = ANY($1)`,
    [rows.map((r) => r.id)]
  )
  const parArticle = new Map<string, AivenListedArticle["ArticleGoogleTag"]>()
  for (const l of liens as Array<{ articleId: string; id: string; name: string; slug: string; color: string | null }>) {
    const seau = parArticle.get(l.articleId) ?? []
    seau.push({ NewsTag: { id: l.id, name: l.name, slug: l.slug, color: l.color } })
    parArticle.set(l.articleId, seau)
  }

  return rows.map((r) => ({
    id: r.id,
    title: r.title,
    link: r.link,
    imageUrl: r.imageUrl ?? null,
    imageCaption: r.imageCaption ?? null,
    source: r.source ?? null,
    description: r.description ?? null,
    publishedAt: ms(r.publishedAt) ?? 0,
    scrapedAt: ms(r.scrapedAt),
    createdAt: ms(r.createdAt),
    updatedAt: ms(r.updatedAt),
    localImage: r.localImage ?? null,
    r2Url: r.r2Url ?? null,
    author: r.author ?? null,
    category: r.category ?? null,
    hidden: Boolean(r.hidden),
    ArticleGoogleTag: parArticle.get(r.id) ?? [],
  }))
}

/** Texte intégral d'un article (panneau de détail de l'admin). */
export async function fetchAivenArticleContent(id: string): Promise<string | null> {
  const { rows } = await getPool().query(`SELECT content FROM "Article" WHERE id = $1`, [id])
  return rows[0]?.content ?? null
}

/**
 * Masque un article.
 *
 * Le bouton « supprimer » de l'admin passe par ici : on masque au lieu
 * d'effacer. La ligne reste la fiche de référence de l'article — le RAG s'y
 * appuie, et sa purge retire de l'index du chat les articles masqués, donc
 * l'effet visible est le même des deux côtés, en réversible.
 */
export async function setAivenArticleHidden(id: string, hidden: boolean): Promise<boolean> {
  const { rowCount } = await getPool().query(
    `UPDATE "Article" SET hidden = $2, "updatedAt" = now() WHERE id = $1`,
    [id, hidden]
  )
  return (rowCount ?? 0) > 0
}
