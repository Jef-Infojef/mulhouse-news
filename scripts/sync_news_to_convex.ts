import "dotenv/config";
import { Client } from "pg";
import { callMutation } from "./convex_client_ts";

// Pont NewsArticle (assocommercants) Supabase → Convex (12/08/2026).
//
// Les actualités internes (`NewsArticle`) du repo privé assocommercants sont
// écrites par `publish-scheduled.ts` dans Supabase (via NEWS_DATABASE_URL),
// tandis que le RAG de MulhouseGPT et Convex lisent désormais la table
// Convex `newsArticles` (restée VIDE). Ce script copie les NewsArticle
// PUBLIÉES vers Convex à chaque run du workflow m68-publish-scheduled
// (toutes les 15 min) — le pont qui referme le trou du cutover.
//
// Sélection : `statusWorkflow = 'PUBLISHED' AND hidden = false`, soit
// EXACTEMENT le sous-ensemble que le RAG lit côté Convex
// (`news_bridge:getRecentNewsArticles` / `getAllNewsArticles` filtrent
// hidden=false + statusWorkflow='PUBLISHED'). Une NewsArticle draft/hidden
// ne doit pas polluer la table Convex.
//
// Normalisation :
//   • dates Supabase (DateTime/timestamptz) → epoch ms (Convex stocke en ms) ;
//   • `null` → champ OMIS (Convex refuse null sur v.optional(...)) : les
//     champs optionnels (excerpt, featuredImage, publishedAt) sont passés en
//     undefined, JSON.stringify les élimine du payload ;
//   • les UUID Supabase restent tels quels : associationId/authorId sont des
//     strings libres, et les liens NewsArticleTag portent l'id Supabase de
//     l'article (`newsArticleId`) + l'id Supabase du tag (`newsTagId`).
//
// Idempotent et rejouable : `migrations:importNewsArticles` déduplique par
// (associationId, slug) et `migrations:importNewsArticleTags` par
// (newsArticleId, newsTagId) — un 2e run n'insère que le delta.
//
// Config (env) :
//   DATABASE_URL (local, .env) OU NEWS_DATABASE_URL (GitHub Actions, pooler) :
//     connexion Supabase lecture+écriture (postgres).
//   CONVEX_DEPLOY_KEY + NEXT_PUBLIC_CONVEX_URL : cible Convex (via le client
//     HTTP `convex_client_ts`).
//
// Usage : npx tsx scripts/sync_news_to_convex.ts

const SUPABASE_URL = process.env.DATABASE_URL || process.env.NEWS_DATABASE_URL || "";

// --- Découpage dynamique des lots (même règle que migrate_supabase_to_convex) --
// Les contenus HTML des news peuvent être volumineux : si un lot de 25 lignes
// dépasse 200 Ko (limite d'args Convex), il est re-découpé en lots de 5.

const MAX_BATCH_ROWS = 25;
const MAX_BATCH_BYTES = 200_000;
const SHORT_BATCH_ROWS = 5;

type Row = Record<string, unknown>;

function makeBatches(rows: Row[]): Row[][] {
  const out: Row[][] = [];
  for (let i = 0; i < rows.length; i += MAX_BATCH_ROWS) {
    const batch = rows.slice(i, i + MAX_BATCH_ROWS);
    if (Buffer.byteLength(JSON.stringify(batch), "utf8") > MAX_BATCH_BYTES) {
      for (let j = 0; j < batch.length; j += SHORT_BATCH_ROWS) {
        out.push(batch.slice(j, j + SHORT_BATCH_ROWS));
      }
    } else {
      out.push(batch);
    }
  }
  return out;
}

// --- Helpers de normalisation pg → Convex ----------------------------------

// DateTime Supabase → epoch ms ; null → undefined
function toMs(v: unknown): number | undefined {
  if (v == null) return undefined;
  if (v instanceof Date) return v.getTime();
  if (typeof v === "number") return v;
  const t = new Date(v as string).getTime();
  return Number.isNaN(t) ? undefined : t;
}

// null → undefined (Convex refuse null sur les champs optionnels : on OMet)
function opt(v: unknown): unknown {
  return v == null ? undefined : v;
}

// --- Orchestration -----------------------------------------------------------

interface ImportCounts {
  read: number;
  inserted: number;
  skipped: number;
  lots: number;
}

async function importArticles(
  pg: Client,
  rows: Row[]
): Promise<ImportCounts> {
  const counts: ImportCounts = { read: rows.length, inserted: 0, skipped: 0, lots: 0 };
  if (rows.length === 0) return counts;
  for (const batch of makeBatches(rows)) {
    counts.lots++;
    const res = await callMutation<{ inserted: number; skipped: number }>(
      "migrations:importNewsArticles",
      { rows: batch }
    );
    counts.inserted += res.inserted;
    counts.skipped += res.skipped;
  }
  return counts;
}

async function importArticleTags(
  pg: Client,
  rows: Row[]
): Promise<ImportCounts> {
  const counts: ImportCounts = { read: rows.length, inserted: 0, skipped: 0, lots: 0 };
  if (rows.length === 0) return counts;
  for (const batch of makeBatches(rows)) {
    counts.lots++;
    const res = await callMutation<{ inserted: number; skipped: number }>(
      "migrations:importNewsArticleTags",
      { rows: batch }
    );
    counts.inserted += res.inserted;
    counts.skipped += res.skipped;
  }
  return counts;
}

async function main() {
  if (!SUPABASE_URL) {
    throw new Error("DATABASE_URL ou NEWS_DATABASE_URL manquant dans l'environnement");
  }
  if (!process.env.CONVEX_DEPLOY_KEY || !process.env.NEXT_PUBLIC_CONVEX_URL) {
    throw new Error("CONVEX_DEPLOY_KEY et NEXT_PUBLIC_CONVEX_URL requis (client Convex)");
  }

  const pg = new Client({
    connectionString: SUPABASE_URL.replace("?pgbouncer=true", "").replace("&pgbouncer=true", ""),
  });
  await pg.connect();

  try {
    // 1. NewsArticle publiées et non cachées (sous-ensemble lu par le RAG).
    const { rows } = await pg.query(
      `SELECT id, "associationId", "authorId", title, slug, content, excerpt,
              "featuredImage", status, "statusWorkflow", "publishedAt", hidden,
              "createdAt", "updatedAt"
       FROM "NewsArticle"
       WHERE "statusWorkflow" = 'PUBLISHED' AND hidden = false
       ORDER BY "createdAt"`
    );
    console.log(
      `[newsArticles] ${rows.length} lignes lues (statusWorkflow=PUBLISHED AND hidden=false)`
    );

    const articleRows: Row[] = rows.map((r: Record<string, unknown>) => ({
      associationId: r.associationId as string,
      authorId: r.authorId as string,
      title: r.title as string,
      slug: r.slug as string,
      content: (r.content as string | null) ?? "",
      excerpt: opt(r.excerpt),
      featuredImage: opt(r.featuredImage),
      status: r.status as string,
      statusWorkflow: r.statusWorkflow as string,
      publishedAt: toMs(r.publishedAt),
      hidden: Boolean(r.hidden),
      createdAt: toMs(r.createdAt) as number,
      updatedAt: toMs(r.updatedAt) as number,
    }));

    const articles = await importArticles(pg, articleRows);
    console.log(
      `[newsArticles] ${articles.lots} lots → +${articles.inserted} insérées, ${articles.skipped} déjà présentes`
    );

    // 2. Liens article → tag (newsArticleId = id Supabase de l'article).
    const articleIds: string[] = rows.map((r: Record<string, unknown>) => r.id as string);
    let tags: ImportCounts = { read: 0, inserted: 0, skipped: 0, lots: 0 };
    if (articleIds.length > 0) {
      const { rows: tagRows } = await pg.query(
        `SELECT "articleId", "tagId" FROM "NewsArticleTag" WHERE "articleId" = ANY($1)`,
        [articleIds]
      );
      const tagRowMapped: Row[] = tagRows.map((r: Record<string, unknown>) => ({
        newsArticleId: r.articleId as string,
        newsTagId: r.tagId as string,
      }));
      console.log(`[newsArticleTags] ${tagRowMapped.length} liens lus`);
      tags = await importArticleTags(pg, tagRowMapped);
      console.log(
        `[newsArticleTags] ${tags.lots} lots → +${tags.inserted} insérés, ${tags.skipped} déjà présents`
      );
    } else {
      console.log("[newsArticleTags] aucun lien (0 article publié)");
    }

    console.log(
      `\nSync terminé : ${articles.read} news lues, +${articles.inserted} insérées, ` +
        `${articles.skipped} déjà présentes | ${tags.read} liens lus, +${tags.inserted} insérés`
    );
  } finally {
    await pg.end();
  }
}

main().catch((err) => {
  console.error("Échec :", (err as Error).message);
  process.exit(1);
});
