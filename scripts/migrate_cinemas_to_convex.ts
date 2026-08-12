import "dotenv/config";
import { Client } from "pg";
import { ConvexHttpClient } from "convex/browser";

// Migration des tables cinéma (Cinema / Movie / Screening) de Supabase vers
// Convex (12/08/2026). Idempotente : les mutations d'import dédupliquent par
// supabaseId (id Prisma d'origine : Cinema.id cuid, Movie.id
// `movie-<allocineId>`, Screening.id `scr-<cinemaId>-<movieId>-...`). Lots
// dynamiques (même mécanique que migrate_outings_to_convex.ts).
//
// Les `supabaseId` Convex = ids Prisma Supabase : c'est la clé qui rendra le
// miroir du scraper (REPO C) cohérent entre les deux stores.

const SUPABASE_URL = process.env.DATABASE_URL || "";
const CONVEX_URL =
  process.env.NEXT_PUBLIC_CONVEX_URL || "https://academic-spoonbill-914.convex.cloud";
const DEPLOY_KEY = process.env.CONVEX_DEPLOY_KEY || "";

const MAX_BATCH_ROWS = 25;
const MAX_BATCH_BYTES = 200_000;
const SHORT_BATCH_ROWS = 5;

function toMs(v: unknown): number | undefined {
  if (v == null) return undefined;
  if (v instanceof Date) return v.getTime();
  if (typeof v === "number") return v;
  return new Date(v as string).getTime();
}

function opt(v: unknown): unknown {
  return v == null ? undefined : v;
}

/** Nombre (Float Prisma) ; pg peut renvoyer une chaîne pour numeric. */
function num(v: unknown): number | undefined {
  if (v == null) return undefined;
  const n = typeof v === "number" ? v : parseFloat(String(v));
  return Number.isFinite(n) ? n : undefined;
}

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

interface TableConfig {
  table: string;
  mutation: string;
  label: string;
  columns: string;
  map: (r: Record<string, unknown>) => Row;
}

const TABLES: TableConfig[] = [
  {
    table: "Cinema",
    mutation: "migrations:importCinemas",
    label: "cinemas",
    columns: `id, name, slug, "allocineId", address, website`,
    map: (r) => ({
      supabaseId: r.id as string,
      name: r.name as string,
      slug: r.slug as string,
      allocineId: String(r.allocineId),
      address: opt(r.address),
      website: opt(r.website),
    }),
  },
  {
    table: "Movie",
    mutation: "migrations:importMovies",
    label: "movies",
    columns: `id, "allocineId", title, "originalTitle", synopsis, "posterUrl",
              "trailerUrl", runtime, genres, director, "cast", "ageRating",
              "userRating", "pressRating", "updatedAt"`,
    map: (r) => ({
      supabaseId: r.id as string,
      allocineId: Number(r.allocineId),
      title: r.title as string,
      originalTitle: opt(r.originalTitle),
      synopsis: opt(r.synopsis),
      posterUrl: opt(r.posterUrl),
      trailerUrl: opt(r.trailerUrl),
      runtime: opt(r.runtime),
      genres: opt(r.genres),
      director: opt(r.director),
      cast: opt(r.cast),
      ageRating: opt(r.ageRating),
      userRating: num(r.userRating),
      pressRating: num(r.pressRating),
      updatedAt: toMs(r.updatedAt),
    }),
  },
  {
    table: "Screening",
    mutation: "migrations:importScreenings",
    label: "screenings",
    columns: `id, "cinemaId", "movieId", "startsAt", "diffusionVersion", projection, "bookingUrl"`,
    map: (r) => ({
      supabaseId: r.id as string,
      cinemaId: r.cinemaId as string, // id Prisma Cinema (supabaseId Convex)
      movieId: r.movieId as string, // id Prisma Movie (supabaseId Convex)
      startsAt: toMs(r.startsAt)!,
      diffusionVersion: r.diffusionVersion as string,
      projection: r.projection as string,
      bookingUrl: opt(r.bookingUrl),
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
    console.log(`\n[${cfg.label}] table "${cfg.table}" absente de Supabase → ignorée`);
    return { inserted: 0, skipped: 0, lots: 0, read: 0 };
  }
  const { rows } = await pg.query(`SELECT ${cfg.columns} FROM "${cfg.table}"`);
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
  console.log(`Migration cinémas Supabase → Convex (${CONVEX_URL})`);

  const pg = new Client({
    connectionString: SUPABASE_URL.replace("?pgbouncer=true", "").replace("&pgbouncer=true", ""),
  });
  await pg.connect();
  const convex = new ConvexHttpClient(CONVEX_URL);
  if (DEPLOY_KEY) {
    (convex as unknown as { setAdminAuth: (t: string) => void }).setAdminAuth(DEPLOY_KEY);
  }

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

  await pg.end();
  console.log("Terminé.");
}

main().catch((err) => {
  console.error("Échec :", err.message);
  process.exit(1);
});
