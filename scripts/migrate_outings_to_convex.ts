import "dotenv/config";
import { createHash } from "crypto";
import { Client } from "pg";
import { ConvexHttpClient } from "convex/browser";

// Migration des tables sorties (Outing / OutingCategory / OutingTag) de
// Supabase vers Convex (12/08/2026). Idempotente : les mutations d'import
// dédupliquent par supabaseId (OutingTag : par couple outingId+categoryId via
// son supabaseId UUID v5 déterministe). Lots dynamiques (même mécanique que
// migrate_supabase_to_convex.ts).

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

// UUID v5 (SHA-1) déterministe — OutingTag n'a pas d'id Prisma (PK composite
// (outingId, categoryId)) : on synthétise un supabaseId stable sur le couple,
// identique côté scraper Python (uuid.uuid5) pour rester cohérent.
function uuidv5(name: string): string {
  const NS_URL = Buffer.from("6ba7b8119dad11d180b400c04fd430c8", "hex");
  const hash = createHash("sha1").update(NS_URL).update(Buffer.from(name, "utf8")).digest();
  hash[6] = (hash[6] & 0x0f) | 0x50;
  hash[8] = (hash[8] & 0x3f) | 0x80;
  const hex = hash.subarray(0, 16).toString("hex");
  return [
    hex.slice(0, 8),
    hex.slice(8, 12),
    hex.slice(12, 16),
    hex.slice(16, 20),
    hex.slice(20),
  ].join("-");
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
    table: "Outing",
    mutation: "migrations:importOutings",
    label: "outings",
    columns: `id, "associationId", title, description, "imageUrl", date, "endDate",
              location, price, link, hidden, "createdAt", "updatedAt"`,
    map: (r) => ({
      supabaseId: r.id,
      associationId: r.associationId,
      title: r.title,
      description: opt(r.description),
      imageUrl: opt(r.imageUrl),
      date: toMs(r.date)!,
      endDate: toMs(r.endDate),
      location: opt(r.location),
      price: opt(r.price),
      link: opt(r.link),
      hidden: Boolean(r.hidden),
      createdAt: toMs(r.createdAt)!,
      updatedAt: toMs(r.updatedAt)!,
    }),
  },
  {
    table: "OutingCategory",
    mutation: "migrations:importOutingCategories",
    label: "outingCategories",
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
    table: "OutingTag",
    mutation: "migrations:importOutingTags",
    label: "outingTags",
    columns: `"outingId", "categoryId"`,
    map: (r) => ({
      supabaseId: uuidv5(`${r.outingId}:${r.categoryId}`),
      outingId: r.outingId as string,
      categoryId: r.categoryId as string,
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
  console.log(`Migration sorties Supabase → Convex (${CONVEX_URL})`);

  const pg = new Client({
    connectionString: SUPABASE_URL.replace("?pgbouncer=true", "").replace("&pgbouncer=true", ""),
  });
  await pg.connect();
  const convex = new ConvexHttpClient(CONVEX_URL);
  // Auth admin via deploy key quand fournie (les mutations d'import restent
  // publicment appelables sinon, comme en Phase 1/6).
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
