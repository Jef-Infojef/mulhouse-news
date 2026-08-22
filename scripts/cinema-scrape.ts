import "dotenv/config";
import { Client } from "pg";

// Scraper des séances de cinéma AlloCiné → Supabase (+ miroir Convex).
//
// Porté depuis le repo assocommercants (lib/cinema-scraper.ts +
// lib/convex-cinema.ts, 08/2026) pour rapprocher le job du backend Convex
// qu'il alimente. Même logique :
//  - Supabase reste le chemin primaire (le site mulhouse68.fr lit via son
//    pont cache avec fallback SQL),
//  - Convex est un miroir non bloquant (double écriture), actif quand
//    CONVEX_DEPLOY_KEY et NEXT_PUBLIC_CONVEX_URL sont définies,
//  - supabaseId Convex = ids Prisma Supabase d'origine (Cinema.id cuid,
//    Movie.id `movie-<allocineId>`, Screening.id
//    `scr-<cinemaId>-<movieId>-<startsAt>-<version>-<projection>`).
//
// Dépendances : pg (root package.json). Exécution : npx tsx scripts/cinema-scrape.ts

const ALLOCINE_BASE = "https://www.allocine.fr/_/showtimes/theater-";
const DAYS_AHEAD = 7;

const VERSION_MAP: Record<string, string> = {
  original: "VO",
  original_st: "VOST",
  original_st_sme: "VOST",
  multiple: "VF",
  multiple_st: "VFST",
  multiple_st_sme: "VFST",
};

// ─── Convex (miroir, même protocole que lib/convex-cinema.ts du repo C) ─────

const CONVEX_URL_ENV = "NEXT_PUBLIC_CONVEX_URL";
const CONVEX_KEY_ENV = "CONVEX_DEPLOY_KEY";

function useConvexCinema(): boolean {
  return Boolean(process.env[CONVEX_KEY_ENV]?.trim() && process.env[CONVEX_URL_ENV]?.trim());
}

function requireConvexConfig(): { url: string; key: string } {
  const url = process.env[CONVEX_URL_ENV]?.trim();
  const key = process.env[CONVEX_KEY_ENV]?.trim();
  if (!url || !key) throw new Error("Convex non configuré");
  return { url, key };
}

// Convex refuse null sur les champs v.optional(...) : il faut les OMETTRE.
function stripNone(args: Record<string, unknown>): Record<string, unknown> {
  const out: Record<string, unknown> = {};
  for (const [k, v] of Object.entries(args)) {
    if (v === undefined || v === null) continue;
    out[k] = v;
  }
  return out;
}

async function callConvex(path: string, args: Record<string, unknown>, mutation: boolean): Promise<unknown> {
  const { url, key } = requireConvexConfig();
  const endpoint = `${url}/api/${mutation ? "mutation" : "query"}`;
  const payload = { path, format: "json", args: stripNone(args) };

  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 90000);
  let resp: Response;
  try {
    resp = await fetch(endpoint, {
      method: "POST",
      signal: controller.signal,
      headers: { Authorization: `Convex ${key}`, "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
  } catch (err) {
    const msg = err instanceof Error ? err.message : String(err);
    throw new Error(`Erreur HTTP Convex (${path}): ${msg}`);
  } finally {
    clearTimeout(timeout);
  }

  if (!resp.ok) {
    const text = await resp.text();
    throw new Error(`Convex HTTP ${resp.status} (${path}): ${text.slice(0, 500)}`);
  }
  const data = (await resp.json()) as { status: string; value?: unknown; errorMessage?: string };
  if (data.status !== "success") {
    throw new Error(`Convex UDF en erreur (${path}): ${data.errorMessage ?? JSON.stringify(data)}`);
  }
  return data.value;
}

interface UpsertScreeningRow {
  supabaseId: string;
  movieId: string;
  startsAt: number; // epoch ms
  diffusionVersion: string;
  projection: string;
  bookingUrl?: string | null;
}

function upsertMovieConvex(row: Record<string, unknown>): Promise<{ created: boolean }> {
  return callConvex("cinemas:upsertMovie", { row: stripNone(row) }, true) as Promise<{ created: boolean }>;
}

function replaceScreeningsForCinemaDay(
  cinemaId: string,
  date: string,
  screenings: UpsertScreeningRow[]
): Promise<{ deleted: number; inserted: number }> {
  return callConvex(
    "cinemas:replaceScreeningsForCinemaDay",
    { cinemaId, date, screenings: screenings.map((s) => stripNone(s as unknown as Record<string, unknown>)) },
    true
  ) as Promise<{ deleted: number; inserted: number }>;
}

// ─── AlloCiné ────────────────────────────────────────────────────────────────

function getProjection(showtime: { tags?: string[] }): string {
  const tags = showtime.tags ?? [];
  if (tags.some((t) => t.includes("3D"))) return "3D";
  if (tags.some((t) => t.includes("IMAX"))) return "IMAX";
  if (tags.some((t) => t.includes("4DX"))) return "4DX";
  return "2D";
}

function getBookingUrl(showtime: {
  data?: { ticketing?: Array<{ type?: string; provider?: string; urls?: string[] }> };
}): string | null {
  const ticketing = showtime.data?.ticketing ?? [];
  const desktop =
    ticketing.find((t) => t.type === "DESKTOP" && t.provider === "default") ??
    ticketing.find((t) => t.type === "DESKTOP");
  return desktop?.urls?.[0] ?? null;
}

async function fetchShowtimes(allocineId: string, date: string): Promise<unknown> {
  const url = `${ALLOCINE_BASE}${allocineId}/d-${date}/`;
  const res = await fetch(url, {
    headers: { "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36" },
    signal: AbortSignal.timeout(8000),
  });
  if (!res.ok) throw new Error(`AlloCiné ${allocineId} ${date}: HTTP ${res.status}`);
  return res.json();
}

interface AllocineMovie {
  title: string;
  originalTitle?: string | null;
  synopsis?: string | null;
  poster?: { url?: string };
  trailerUrl?: string | null;
  runtime?: number | string | null;
  genres?: Array<{ translate?: string }>;
  credits?: Array<{ position?: { name?: string }; person?: { firstName?: string; lastName?: string } }>;
  cast?: { edges?: Array<{ node?: { actor?: { firstName?: string; lastName?: string } } }> };
  releases?: Array<{ certificate?: { label?: string } }>;
  stats?: { userRating?: { score?: number }; pressReview?: { score?: number } };
  internalId?: number;
}

function extractMovieData(m: AllocineMovie) {
  const poster = m.poster;
  const genres = m.genres;
  const credits = m.credits;
  const cast = m.cast;
  const releases = m.releases;
  const stats = m.stats;

  return {
    title: m.title,
    originalTitle: m.originalTitle ?? null,
    synopsis: m.synopsis ?? null,
    posterUrl: poster?.url ?? null,
    trailerUrl: m.trailerUrl ?? null,
    runtime: m.runtime != null ? String(m.runtime) : null,
    genres: genres?.map((g) => g.translate).join(", ") ?? null,
    director: (() => {
      try {
        const p = credits?.find((c) => c.position?.name === "DIRECTOR")?.person;
        return p ? `${p.firstName ?? ""} ${p.lastName ?? ""}`.trim() || null : null;
      } catch {
        return null;
      }
    })(),
    cast: (() => {
      try {
        return (
          cast?.edges
            ?.slice(0, 5)
            .map((e) => {
              const a = e.node?.actor;
              return a ? `${a.firstName ?? ""} ${a.lastName ?? ""}`.trim() : null;
            })
            .filter(Boolean)
            .join(", ") || null
        );
      } catch {
        return null;
      }
    })(),
    ageRating: releases?.[0]?.certificate?.label ?? null,
    userRating: stats?.userRating?.score ?? null,
    pressRating: stats?.pressReview?.score ?? null,
  };
}

// ─── Run ─────────────────────────────────────────────────────────────────────

export interface CinemaScrapeResult {
  success: boolean;
  totalMovies: number;
  totalScreenings: number;
  errors?: string[];
  duration: number;
}

const MOVIE_COLUMNS = `"id", "allocineId", "title", "originalTitle", "synopsis", "posterUrl",
  "trailerUrl", "runtime", "genres", "director", "cast", "ageRating",
  "userRating", "pressRating", "updatedAt"`;

export async function runCinemaScrape(): Promise<CinemaScrapeResult> {
  const startTime = Date.now();
  console.log(`🎬 [CINEMA SCRAPE] Starting at ${new Date().toISOString()}`);

  // Miroir Convex (double écriture) : NON BLOQUANT — erreurs tracées seulement.
  const mirrorEnabled = useConvexCinema();
  const mirrorJobs: Promise<unknown>[] = [];
  const mirror = (p: Promise<unknown>) => {
    mirrorJobs.push(
      p.catch((err) => console.error(`[CONVEX MIRROR] ${err instanceof Error ? err.message : String(err)}`))
    );
  };
  if (mirrorEnabled) console.log("🎬 [CINEMA SCRAPE] Miroir Convex activé (double écriture)");

  const client = new Client({ connectionString: process.env.DATABASE_URL });
  await client.connect();

  let totalScreenings = 0;
  let totalMovies = 0;
  const errors: string[] = [];

  try {
    const cinemasRes = await client.query<{
      id: string;
      name: string;
      slug: string;
      allocineId: string;
    }>(`SELECT id, name, slug, "allocineId" FROM "Cinema"`);
    const cinemas = cinemasRes.rows;
    if (!cinemas.length) throw new Error("Aucun cinéma en base");

    const dates: string[] = [];
    for (let i = 0; i < DAYS_AHEAD; i++) {
      const d = new Date();
      d.setDate(d.getDate() + i);
      dates.push(d.toISOString().substring(0, 10));
    }

    const tasks = cinemas.flatMap((cinema) => dates.map((date) => ({ cinema, date })));
    const fetched = await Promise.allSettled(
      tasks.map(({ cinema, date }) =>
        fetchShowtimes(cinema.allocineId, date).then((data) => ({ cinema, date, data }))
      )
    );

    for (const result of fetched) {
      if (result.status === "rejected") {
        errors.push(result.reason?.message ?? "fetch error");
        continue;
      }

      const { cinema, date, data } = result.value as {
        cinema: (typeof cinemas)[number];
        date: string;
        data: { error?: unknown; results?: Array<Record<string, unknown>> };
      };

      if (data.error || !data.results?.length) continue;

      try {
        const dayStart = new Date(`${date}T00:00:00`);
        const dayEnd = new Date(`${date}T23:59:59`);
        await client.query(`DELETE FROM "Screening" WHERE "cinemaId" = $1 AND "startsAt" >= $2 AND "startsAt" <= $3`, [
          cinema.id,
          dayStart,
          dayEnd,
        ]);

        // Séances écrites pour ce cinéma/jour, à répliquer en Convex en fin de
        // bloc (replaceScreeningsForCinemaDay = delete + insert atomiques).
        const mirroredScreenings: UpsertScreeningRow[] = [];

        for (const item of data.results) {
          const m = item.movie as AllocineMovie | undefined;
          if (!m?.internalId) continue;

          const movieFields = extractMovieData(m);
          const internalId = m.internalId;
          const movieUpsert = await client.query<{ id: string }>(
            `INSERT INTO "Movie" (${MOVIE_COLUMNS})
             VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14,now())
             ON CONFLICT ("allocineId") DO UPDATE SET
               "title"=EXCLUDED."title", "originalTitle"=EXCLUDED."originalTitle",
               "synopsis"=EXCLUDED."synopsis", "posterUrl"=EXCLUDED."posterUrl",
               "trailerUrl"=EXCLUDED."trailerUrl", "runtime"=EXCLUDED."runtime",
               "genres"=EXCLUDED."genres", "director"=EXCLUDED."director",
               "cast"=EXCLUDED."cast", "ageRating"=EXCLUDED."ageRating",
               "userRating"=EXCLUDED."userRating", "pressRating"=EXCLUDED."pressRating",
               "updatedAt"=now()
             RETURNING id`,
            [
              `movie-${internalId}`,
              internalId,
              movieFields.title,
              movieFields.originalTitle,
              movieFields.synopsis,
              movieFields.posterUrl,
              movieFields.trailerUrl,
              movieFields.runtime,
              movieFields.genres,
              movieFields.director,
              movieFields.cast,
              movieFields.ageRating,
              movieFields.userRating,
              movieFields.pressRating,
            ]
          );
          const movieId = movieUpsert.rows[0].id;
          totalMovies++;

          // Miroir Convex du film : supabaseId = id Prisma Movie (`movie-<id>`).
          if (mirrorEnabled) {
            mirror(upsertMovieConvex({ supabaseId: movieId, allocineId: internalId, ...movieFields }));
          }

          const showtimes = item.showtimes as Record<string, Array<Record<string, unknown>>> | undefined;
          for (const [versionKey, versionLabel] of Object.entries(VERSION_MAP)) {
            const versionShowtimes = showtimes?.[versionKey] ?? [];
            for (const st of versionShowtimes) {
              const projection = getProjection(st as { tags?: string[] });
              const bookingUrl = getBookingUrl(st as Parameters<typeof getBookingUrl>[0]);
              const screeningId = `scr-${cinema.id}-${movieId}-${st.startsAt}-${versionLabel}-${projection}`;
              try {
                await client.query(
                  `INSERT INTO "Screening"
                     ("id","cinemaId","movieId","startsAt","diffusionVersion","projection","bookingUrl")
                   VALUES ($1,$2,$3,$4,$5,$6,$7)
                   ON CONFLICT DO NOTHING`,
                  [screeningId, cinema.id, movieId, new Date(st.startsAt as string), versionLabel, projection, bookingUrl]
                );
                totalScreenings++;
                // Miroir de la séance : supabaseId = id Prisma Screening.
                mirroredScreenings.push({
                  supabaseId: screeningId,
                  movieId,
                  startsAt: new Date(st.startsAt as string).getTime(),
                  diffusionVersion: versionLabel,
                  projection,
                  bookingUrl,
                });
              } catch {
                // Ignore duplicate screenings
              }
            }
          }
        }

        // Miroir du jour : remplace les séances du cinéma pour ce jour en Convex.
        if (mirrorEnabled) {
          mirror(replaceScreeningsForCinemaDay(cinema.id, date, mirroredScreenings));
        }
      } catch (err: unknown) {
        const message = err instanceof Error ? err.message : String(err);
        errors.push(`${cinema.slug} ${date}: ${message}`);
        console.error(`❌ [CINEMA SCRAPE] Error ${cinema.slug} ${date}:`, message);
      }
    }
  } finally {
    await client.end().catch(() => {});
  }

  const duration = parseFloat(((Date.now() - startTime) / 1000).toFixed(2));
  console.log(
    `✅ [CINEMA SCRAPE] Completed at ${new Date().toISOString()} — Duration: ${duration}s — ${totalMovies} movies, ${totalScreenings} screenings`
  );

  try {
    const logClient = new Client({ connectionString: process.env.DATABASE_URL });
    await logClient.connect();
    await logClient.query(
      `INSERT INTO "ScrapeLog" ("id","type","status","duration","totalMovies","totalScreenings","errors")
       VALUES ($1,'cinema',$2,$3,$4,$5,$6)`,
      [
        crypto.randomUUID(),
        errors.length === 0 ? "success" : "failure",
        duration,
        totalMovies,
        totalScreenings,
        errors.length > 0 ? errors.join("\n").substring(0, 1000) : null,
      ]
    );
    await logClient.end();
  } catch (logErr) {
    console.error("Failed to save scrape log:", logErr instanceof Error ? logErr.message : logErr);
  }

  // Laisse les miroirs Convex se terminer (erreurs déjà tracées, non bloquant).
  if (mirrorJobs.length) {
    await Promise.allSettled(mirrorJobs);
  }

  return {
    success: errors.length === 0,
    totalMovies,
    totalScreenings,
    errors: errors.length ? errors : undefined,
    duration,
  };
}

async function main() {
  const result = await runCinemaScrape();
  console.log(JSON.stringify(result, null, 2));
  if (!result.success) process.exit(1);
}

main().catch((error) => {
  console.error("❌ Erreur:", error);
  process.exit(1);
});
