import "dotenv/config";
import { Client } from "pg";
import { ConvexHttpClient } from "convex/browser";

// Vérification des compteurs Supabase vs Convex, table par table.
// ScrapingLog peut diverger si les scrapers GitHub écrivent en parallèle
// (tolérance de 5 % affichée comme "~").

const SUPABASE_URL = process.env.DATABASE_URL || "";
const CONVEX_URL = process.env.NEXT_PUBLIC_CONVEX_URL || "http://127.0.0.1:3210";

const TABLES = [
  { table: "Article", collection: "articles" },
  { table: "ArticleImage", collection: "articleImages" },
  { table: "ScrapingLog", collection: "scrapingLogs" },
  { table: "AppConfig", collection: "appConfig" },
  { table: "WeatherHistory", collection: "weatherHistory" },
  { table: "ArticleGoogleTag", collection: "articleGoogleTags" },
  { table: "NewsArticle", collection: "newsArticles" },
  { table: "NewsArticleTag", collection: "newsArticleTags" },
  { table: "NewsTag", collection: "newsTags" },
];

async function main() {
  if (!SUPABASE_URL) throw new Error("DATABASE_URL manquant dans .env");

  const pg = new Client({
    connectionString: SUPABASE_URL.replace("?pgbouncer=true", "").replace("&pgbouncer=true", ""),
  });
  await pg.connect();

  const supabaseCounts: Record<string, number> = {};
  const missingTables: string[] = [];
  for (const { table } of TABLES) {
    const { rows: tblRows } = await pg.query(
      "SELECT 1 FROM pg_tables WHERE schemaname = 'public' AND tablename = $1",
      [table]
    );
    if (tblRows.length === 0) {
      missingTables.push(table);
      supabaseCounts[table] = -1;
      continue;
    }
    const { rows } = await pg.query(`SELECT count(*) AS n FROM "${table}"`);
    supabaseCounts[table] = Number(rows[0].n);
  }

  const shared = Number(
    (await pg.query('SELECT extract(epoch FROM max("startedAt")) * 1000 AS ms FROM "ScrapingLog"')).rows[0].ms ?? 0
  );
  await pg.end();

  const convex = new ConvexHttpClient(CONVEX_URL);
  const convexCounts: Record<string, number> = {};
  for (const { collection } of TABLES) {
    let n = 0;
    let cursor: string | null = null;
    do {
      const page = (await convex.query("stats:countTablePage", {
        table: collection,
        cursor,
      })) as { count: number; isDone: boolean; continueCursor: string | null };
      n += page.count;
      cursor = page.isDone ? null : page.continueCursor;
    } while (cursor);
    convexCounts[collection] = n;
  }

  console.log(`Supabase : ${SUPABASE_URL.split("@")[1]?.split("/")[0] ?? "?"}`);
  console.log(`Convex   : ${CONVEX_URL}`);
  console.log("\nTable Supabase          Supabase  Convex    Diff    Statut");
  console.log("-".repeat(58));

  let ok = true;
  for (const { table, collection } of TABLES) {
    const sb = supabaseCounts[table];
    const cv = convexCounts[collection] ?? 0;
    if (sb === -1) {
      const status = cv === 0 ? "OK (table absente des 2 côtés)" : "ÉCART (table absente Supabase)";
      if (cv !== 0) ok = false;
      console.log(`${table.padEnd(21)} ${"absent".padStart(8)} ${String(cv).padStart(7)} ${"".padStart(6)}  ${status}`);
      continue;
    }
    const diff = cv - sb;
    const pct = sb > 0 ? Math.abs(diff / sb) : diff === 0 ? 0 : Infinity;
    let status: string;
    if (diff === 0) status = "OK";
    else if (collection === "scrapingLogs" && pct <= 0.05) status = "~ (±5%, scraper actif)";
    else if (pct <= 0.01) status = "OK (≈, écart <1%)";
    else status = "ÉCART";
    if (status === "ÉCART") ok = false;
    console.log(
      `${table.padEnd(21)} ${String(sb).padStart(8)} ${String(cv).padStart(7)} ${String(diff >= 0 ? `+${diff}` : diff).padStart(6)}  ${status}`
    );
  }

  if (shared > 0) {
    const ageMin = Math.round((Date.now() - shared) / 60000);
    console.log("\nDernier ScrapingLog Supabase : il y a ~" + ageMin + " min");
    if (ageMin < 15) console.log("→ des scrapers GitHub ont très probablement écrit en parallèle (écart ScrapingLog possible).");
  }

  console.log(ok ? "\nTous les compteurs concordent." : "\nÉcarts détectés — voir ci-dessus.");
  process.exit(ok ? 0 : 1);
}

main().catch((err) => {
  console.error("Échec :", err.message);
  process.exit(1);
});