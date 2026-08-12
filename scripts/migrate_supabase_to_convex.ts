import "dotenv/config";
import { Client } from "pg";
import { ConvexHttpClient } from "convex/browser";

// Migration complète Supabase → Convex (Phase 1).
// IMPORT_LIMIT : absent ou 0 = tout migrer ; >0 = limite les gros volumes
// (Article et NewsArticle) pour les tests, le reste est migré en entier.
// Les lots sont découpés dynamiquement : si la taille JSON d'un lot de 25 lignes
// dépasse 200 Ko (limite d'args Convex), il est re-découpé en lots de 5.

const SUPABASE_URL = process.env.DATABASE_URL || "";
const CONVEX_URL = process.env.NEXT_PUBLIC_CONVEX_URL || "http://127.0.0.1:3210";
const IMPORT_LIMIT = Number(process.env.IMPORT_LIMIT || 0);

const MAX_BATCH_ROWS = 25;
const MAX_BATCH_BYTES = 200_000;
const SHORT_BATCH_ROWS = 5;

// --- Helpers de normalisation pg → Convex --------------------------------

// DateTime Prisma → epoch ms ; null → undefined
function toMs(v: unknown): number | undefined {
  if (v == null) return undefined;
  if (v instanceof Date) return v.getTime();
  if (typeof v === "number") return v;
  return new Date(v as string).getTime();
}

// pg renvoie les float8/float4 en strings et les bigint en strings
function toNum(v: unknown): number {
  return typeof v === "number" ? v : Number(v);
}

function opt(v: unknown): unknown {
  return v == null ? undefined : v;
}

// pg parse déjà le JSONB ; sécurité si une chaîne traîne
function toAny(v: unknown): unknown {
  if (v == null) return undefined;
  if (typeof v === "string") {
    try {
      return JSON.parse(v);
    } catch {
      return undefined;
    }
  }
  return v;
}

// --- Découpage dynamique des lots ----------------------------------------

type Row = Record<string, unknown>;

function makeBatches(rows: Row[]): Row[][] {
  const out: Row[][] = [];
  for (let i = 0; i < rows.length; i += MAX_BATCH_ROWS) {
    const batch = rows.slice(i, i + MAX_BATCH_ROWS);
    if (Buffer.byteLength(JSON.stringify(batch), "utf8") > MAX_BATCH_BYTES) {
      // Lot trop volumineux (articles HTML) : on réduit à SHORT_BATCH_ROWS lignes
      for (let j = 0; j < batch.length; j += SHORT_BATCH_ROWS) {
        out.push(batch.slice(j, j + SHORT_BATCH_ROWS));
      }
    } else {
      out.push(batch);
    }
  }
  return out;
}

// --- Backfill supabaseId (Phase 2) -----------------------------------------

// Les documents importés en Phase 1 n'ont pas de champ supabaseId : il faut le
// backfiller pour que les jointures articleGoogleTags/articleImages (qui
// stockent l'UUID Supabase) fonctionnent côté Convex. Idempotent : match par
// clé naturelle (link / associationId+slug), patch seulement si différent.

async function backfillSupabaseIds(
  convex: ConvexHttpClient,
  pg: Client,
  {
    table,
    mutation,
    columns,
  }: {
    table: string;
    mutation: string;
    columns: string;
  }
): Promise<{ read: number; updated: number }> {
  const { rows } = await pg.query(`SELECT ${columns} FROM "${table}"`);
  console.log(`[backfill ${table}] ${rows.length} lignes lues...`);
  let updated = 0;
  for (const batch of makeBatches(rows)) {
    const res = await convex.mutation(mutation, { rows: batch });
    updated += res.updated;
  }
  console.log(`[backfill ${table}] +${updated} supabaseId mis à jour`);
  return { read: rows.length, updated };
}

// --- Orchestration ---------------------------------------------------------

interface TableConfig {
  table: string; // nom de la table Supabase
  mutation: string; // mutation Convex cible
  label: string; // affichage
  columns: string; // colonnes à sélectionner
  map: (r: Record<string, unknown>) => Row;
  limitable?: boolean; // soumise à IMPORT_LIMIT
}

const TABLES: TableConfig[] = [
  {
    table: "NewsTag",
    mutation: "migrations:importNewsTags",
    label: "newsTags",
    columns: `id, "associationId", name, slug, color, "createdAt", "updatedAt"`,
    map: (r) => ({
      supabaseId: r.id,
      associationId: r.associationId,
      name: r.name,
      slug: r.slug,
      color: opt(r.color),
      createdAt: toMs(r.createdAt)!,
      updatedAt: toMs(r.updatedAt)!,
    }),
  },
  {
    table: "NewsArticle",
    mutation: "migrations:importNewsArticles",
    label: "newsArticles",
    limitable: true,
    columns: `"associationId", "authorId", title, slug, content, excerpt, "featuredImage",
              status, "statusWorkflow", "publishedAt", hidden, "createdAt", "updatedAt"`,
    map: (r) => ({
      associationId: r.associationId,
      authorId: r.authorId,
      title: r.title,
      slug: r.slug,
      content: r.content,
      excerpt: opt(r.excerpt),
      featuredImage: opt(r.featuredImage),
      status: r.status,
      statusWorkflow: r.statusWorkflow,
      publishedAt: toMs(r.publishedAt),
      hidden: Boolean(r.hidden),
      createdAt: toMs(r.createdAt)!,
      updatedAt: toMs(r.updatedAt)!,
    }),
  },
  {
    table: "NewsArticleTag",
    mutation: "migrations:importNewsArticleTags",
    label: "newsArticleTags",
    columns: `"articleId" AS "newsArticleId", "tagId" AS "newsTagId"`,
    map: (r) => ({ newsArticleId: r.newsArticleId, newsTagId: r.newsTagId }),
  },
  {
    table: "Article",
    mutation: "migrations:importArticles",
    label: "articles",
    limitable: true,
    columns: `id, title, link, "imageUrl", "imageCaption", source, description, "publishedAt",
              "scrapedAt", "createdAt", "updatedAt", content, "localImage", "r2Url", hidden`,
    map: (r) => ({
      supabaseId: r.id,
      title: r.title,
      link: r.link,
      imageUrl: opt(r.imageUrl),
      imageCaption: opt(r.imageCaption),
      source: opt(r.source),
      description: opt(r.description),
      publishedAt: toMs(r.publishedAt)!,
      scrapedAt: toMs(r.scrapedAt)!,
      createdAt: toMs(r.createdAt)!,
      updatedAt: toMs(r.updatedAt)!,
      content: opt(r.content),
      localImage: opt(r.localImage),
      r2Url: opt(r.r2Url),
      hidden: Boolean(r.hidden),
    }),
  },
  {
    table: "ArticleImage",
    mutation: "migrations:importArticleImages",
    label: "articleImages",
    columns: `"articleId", url, caption, position, "localImage", "r2Url", source, "createdAt"`,
    map: (r) => ({
      articleId: r.articleId,
      url: r.url,
      caption: opt(r.caption),
      position: toNum(r.position),
      localImage: opt(r.localImage),
      r2Url: opt(r.r2Url),
      source: opt(r.source),
      createdAt: toMs(r.createdAt)!,
    }),
  },
  {
    table: "ArticleGoogleTag",
    mutation: "migrations:importArticleGoogleTags",
    label: "articleGoogleTags",
    columns: `"articleId", "tagId"`,
    map: (r) => ({ articleId: r.articleId, tagId: r.tagId }),
  },
  {
    table: "AppConfig",
    mutation: "migrations:importAppConfig",
    label: "appConfig",
    columns: `key, value, "updatedAt"`,
    map: (r) => ({ key: r.key, value: r.value, updatedAt: toMs(r.updatedAt)! }),
  },
  {
    table: "ScrapingLog",
    mutation: "migrations:importScrapingLogs",
    label: "scrapingLogs",
    columns: `"startedAt", "finishedAt", status, "isConnected", "articlesCount",
              "successCount", "errorCount", details, "errorMessage"`,
    map: (r) => ({
      startedAt: toMs(r.startedAt)!,
      finishedAt: toMs(r.finishedAt),
      status: r.status,
      isConnected: Boolean(r.isConnected),
      articlesCount: toNum(r.articlesCount),
      successCount: toNum(r.successCount),
      errorCount: toNum(r.errorCount),
      details: toAny(r.details),
      errorMessage: opt(r.errorMessage),
    }),
  },
  {
    table: "WeatherHistory",
    mutation: "migrations:importWeatherHistory",
    label: "weatherHistory",
    columns: `location, day, month, year, "tempMax", "tempMin", "weatherCode", "createdAt"`,
    map: (r) => ({
      location: r.location,
      day: toNum(r.day),
      month: toNum(r.month),
      year: toNum(r.year),
      tempMax: toNum(r.tempMax),
      tempMin: toNum(r.tempMin),
      weatherCode: toNum(r.weatherCode),
      createdAt: toMs(r.createdAt)!,
    }),
  },
];

async function migrateTable(
  convex: ConvexHttpClient,
  pg: Client,
  cfg: TableConfig
): Promise<{ inserted: number; skipped: number; lots: number; read: number }> {
  const { rows: tblRows } = await pg.query(
    "SELECT 1 FROM pg_tables WHERE schemaname = 'public' AND tablename = $1",
    [cfg.table]
  );
  if (tblRows.length === 0) {
    // Table déclarée dans Prisma mais absente de la base (ex. WeatherHistory) : rien à migrer.
    console.log(`\n[${cfg.label}] table "${cfg.table}" absente de Supabase → ignorée`);
    return { inserted: 0, skipped: 0, lots: 0, read: 0 };
  }
  const limit = cfg.limitable && IMPORT_LIMIT > 0 ? IMPORT_LIMIT : undefined;
  const order = cfg.limitable && limit ? ` ORDER BY "${cfg.table === "Article" ? "publishedAt" : "createdAt"}" DESC` : "";
  const sql = `SELECT ${cfg.columns} FROM "${cfg.table}"${order}${limit ? ` LIMIT ${limit}` : ""}`;
  const { rows } = await pg.query(sql);
  const mapped = rows.map((r) => cfg.map(r));
  console.log(`\n[${cfg.label}] ${mapped.length} lignes lues...`);

  let inserted = 0;
  let skipped = 0;
  let lots = 0;
  for (const batch of makeBatches(mapped)) {
    lots++;
    const res = await convex.mutation(cfg.mutation, { rows: batch });
    inserted += res.inserted;
    skipped += res.skipped;
  }
  console.log(`[${cfg.label}] ${lots} lots → +${inserted} insérés, ${skipped} déjà présents`);
  return { inserted, skipped, lots, read: mapped.length };
}

async function main() {
  if (!SUPABASE_URL) throw new Error("DATABASE_URL manquant dans .env");
  const showLimit = IMPORT_LIMIT > 0 ? `limite ${IMPORT_LIMIT} (Article + NewsArticle)` : "tout";
  console.log(`Export Supabase → Convex (${CONVEX_URL}) — mode : ${showLimit}`);

  const pg = new Client({
    connectionString: SUPABASE_URL.replace("?pgbouncer=true", "").replace("&pgbouncer=true", ""),
  });
  await pg.connect();
  const convex = new ConvexHttpClient(CONVEX_URL);

  const results: Record<string, { inserted: number; skipped: number; lots: number; read: number }> = {};
  for (const cfg of TABLES) {
    try {
      results[cfg.label] = await migrateTable(convex, pg, cfg);
    } catch (err) {
      console.error(`[${cfg.label}] ÉCHEC :`, (err as Error).message);
      results[cfg.label] = { inserted: 0, skipped: 0, lots: 0, read: 0 };
    }
  }

  console.log("\n=== RÉCAPITULATIF ===");
  let totalInserted = 0;
  let totalSkipped = 0;
  for (const [label, r] of Object.entries(results)) {
    totalInserted += r.inserted;
    totalSkipped += r.skipped;
    console.log(
      `${label.padEnd(18)} lu ${String(r.read).padStart(6)} | lots ${String(r.lots).padStart(4)} | +${String(r.inserted).padStart(6)} insérés | ${r.skipped} déjà présents`
    );
  }
  console.log(`\nTotal : ${totalInserted} insérés, ${totalSkipped} déjà présents`);

  console.log("\n=== BACKFILL supabaseId (articles + newsTags) ===");
  const backfillArticles = await backfillSupabaseIds(convex, pg, {
    table: "Article",
    mutation: "app:setArticleSupabaseIds",
    columns: `link, id AS "supabaseId"`,
  });
  const backfillTags = await backfillSupabaseIds(convex, pg, {
    table: "NewsTag",
    mutation: "app:setNewsTagSupabaseIds",
    columns: `"associationId", slug, id AS "supabaseId"`,
  });
  console.log(
    `Backfill terminé : ${backfillArticles.updated} articles, ${backfillTags.updated} newsTags`
  );

  await pg.end();
  console.log("Terminé.");
}

main().catch((err) => {
  console.error("Échec :", err.message);
  process.exit(1);
});