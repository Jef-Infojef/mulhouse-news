import { mutation, query } from "./_generated/server";
import { v } from "convex/values";

// ─────────────────────────────────────────────────────────────────────────────
// Cinémas / films / séances — fonctions Convex des collections cinemas/movies/
// screenings (port Supabase → Convex, 12/08/2026).
//
// Consommées par :
//  • le scraper REPO C `lib/cinema-scraper.ts` via `lib/convex-cinema.ts`
//    (endpoints /api/query + /api/mutation) — miroir NON BLOQUANT en double
//    écriture avec Supabase (le site assocommercants.fr lit encore Supabase,
//    le miroir alimente le cutover + le RAG MulhouseGPT) ;
//  • les ponts caches REPO C `lib/cinema-cache.ts` et REPO B (MulhouseGPT)
//    `lib/cinema-cache.ts` — lectures getCinemas / getScreeningsWithMovieCinema.
//
// Conventions (identiques aux autres collections) :
//  • `supabaseId` = **id Prisma Supabase d'origine** : Cinema.id (cuid),
//    Movie.id (`movie-<allocineId>`), Screening.id (`scr-<cinemaId>-<movieId>-...`).
//    C'est ce que le scraper connaît localement → le miroir reste cohérent
//    entre les deux stores sans table de mapping.
//  • Les clés de relation (cinemaId, movieId) référencent ces supabaseId,
//    jamais des v.id() Convex.
//  • Dates Prisma → epoch ms (v.number()).
//  • Convex refuse `null` sur les champs v.optional(...) : les clients
//    omettent les champs None/undefined avant l'appel.
// ─────────────────────────────────────────────────────────────────────────────

const CINEMA_ROW = v.object({
  supabaseId: v.string(),
  name: v.string(),
  slug: v.string(),
  allocineId: v.string(),
  address: v.optional(v.string()),
  website: v.optional(v.string()),
});

const MOVIE_ROW = v.object({
  supabaseId: v.string(),
  allocineId: v.number(),
  title: v.string(),
  originalTitle: v.optional(v.string()),
  synopsis: v.optional(v.string()),
  posterUrl: v.optional(v.string()),
  trailerUrl: v.optional(v.string()),
  runtime: v.optional(v.string()),
  genres: v.optional(v.string()),
  director: v.optional(v.string()),
  cast: v.optional(v.string()),
  ageRating: v.optional(v.string()),
  userRating: v.optional(v.number()),
  pressRating: v.optional(v.number()),
  updatedAt: v.optional(v.number()),
});

const SCREENING_ROW = v.object({
  supabaseId: v.string(),
  movieId: v.string(), // supabaseId du Movie (id Prisma Movie)
  startsAt: v.number(), // epoch ms
  diffusionVersion: v.string(),
  projection: v.string(),
  bookingUrl: v.optional(v.string()),
});

// ─────────────────────────────────────────────────────────────────────────────
// Mutations
// ─────────────────────────────────────────────────────────────────────────────

/**
 * Upsert d'un cinéma. Dédup par supabaseId (id Prisma Cinema). Si le cinéma
 * n'existe pas encore sous ce supabaseId mais qu'un autre document porte le
 * même allocineId (cas d'un id Prisma régénéré), on patche son supabaseId pour
 * le faire pointer sur l'id actuel.
 */
export const upsertCinema = mutation({
  args: { row: CINEMA_ROW },
  handler: async (ctx, { row }) => {
    const existing = await ctx.db
      .query("cinemas")
      .withIndex("by_supabaseId", (q) => q.eq("supabaseId", row.supabaseId))
      .first();

    if (existing) {
      const patch: Record<string, unknown> = {};
      const keys = ["name", "slug", "allocineId", "address", "website"] as const;
      for (const key of keys) {
        if (row[key] !== undefined) patch[key] = row[key];
      }
      await ctx.db.patch(existing._id, patch);
      return { created: false, id: existing._id, supabaseId: existing.supabaseId };
    }

    // Pas de doc sous ce supabaseId : check allocineId (id Prisma régénéré).
    const byAllocine = await ctx.db
      .query("cinemas")
      .withIndex("by_allocineId", (q) => q.eq("allocineId", row.allocineId))
      .first();
    if (byAllocine) {
      await ctx.db.patch(byAllocine._id, { supabaseId: row.supabaseId });
      return { created: false, id: byAllocine._id, supabaseId: row.supabaseId };
    }

    const id = await ctx.db.insert("cinemas", {
      supabaseId: row.supabaseId,
      name: row.name,
      slug: row.slug,
      allocineId: row.allocineId,
      address: row.address,
      website: row.website,
    });
    return { created: true, id, supabaseId: row.supabaseId };
  },
});

/**
 * Upsert d'un film. Dédup par supabaseId (id Prisma Movie `movie-<allocineId>`)
 * puis par allocineId (id Prisma régénéré → patch du supabaseId).
 */
export const upsertMovie = mutation({
  args: { row: MOVIE_ROW },
  handler: async (ctx, { row }) => {
    const existing = await ctx.db
      .query("movies")
      .withIndex("by_supabaseId", (q) => q.eq("supabaseId", row.supabaseId))
      .first();

    if (existing) {
      const patch: Record<string, unknown> = {};
      const keys = [
        "allocineId",
        "title",
        "originalTitle",
        "synopsis",
        "posterUrl",
        "trailerUrl",
        "runtime",
        "genres",
        "director",
        "cast",
        "ageRating",
        "userRating",
        "pressRating",
      ] as const;
      for (const key of keys) {
        if (row[key] !== undefined) patch[key] = row[key];
      }
      patch["updatedAt"] = row.updatedAt ?? Date.now();
      await ctx.db.patch(existing._id, patch);
      return { created: false, id: existing._id, supabaseId: existing.supabaseId };
    }

    const byAllocine = await ctx.db
      .query("movies")
      .withIndex("by_allocineId", (q) => q.eq("allocineId", row.allocineId))
      .first();
    if (byAllocine) {
      await ctx.db.patch(byAllocine._id, { supabaseId: row.supabaseId });
      return { created: false, id: byAllocine._id, supabaseId: row.supabaseId };
    }

    const id = await ctx.db.insert("movies", {
      supabaseId: row.supabaseId,
      allocineId: row.allocineId,
      title: row.title,
      originalTitle: row.originalTitle,
      synopsis: row.synopsis,
      posterUrl: row.posterUrl,
      trailerUrl: row.trailerUrl,
      runtime: row.runtime,
      genres: row.genres,
      director: row.director,
      cast: row.cast,
      ageRating: row.ageRating,
      userRating: row.userRating,
      pressRating: row.pressRating,
      updatedAt: row.updatedAt ?? Date.now(),
    });
    return { created: true, id, supabaseId: row.supabaseId };
  },
});

/**
 * Remplace les séances d'un cinéma pour un jour donné : suppression de toutes
 * les séances du cinéma dont startsAt tombe dans [début de jour, fin de jour]
 * (équivalent du `screening.deleteMany` du scraper) puis insertion des
 * nouvelles. Retourne {deleted, inserted}.
 *
 * `date` est au format `YYYY-MM-DD` ; début/fin de jour calculés en heure
 * locale (même logique que `new Date(\`${date}T00:00:00\`)` du scraper — les
 * runs GitHub Actions sont en UTC, cohérents).
 */
export const replaceScreeningsForCinemaDay = mutation({
  args: {
    cinemaId: v.string(), // supabaseId du Cinema (id Prisma Cinema)
    date: v.string(), // YYYY-MM-DD
    screenings: v.array(SCREENING_ROW),
  },
  handler: async (ctx, { cinemaId, date, screenings }) => {
    const dayStart = new Date(`${date}T00:00:00`).getTime();
    const dayEnd = new Date(`${date}T23:59:59`).getTime();

    const old = await ctx.db
      .query("screenings")
      .withIndex("by_cinemaId", (q) => q.eq("cinemaId", cinemaId))
      .filter((q) =>
        q.and(q.gte(q.field("startsAt"), dayStart), q.lte(q.field("startsAt"), dayEnd))
      )
      .collect();
    for (const doc of old) await ctx.db.delete(doc._id);

    for (const s of screenings) {
      await ctx.db.insert("screenings", {
        supabaseId: s.supabaseId,
        cinemaId,
        movieId: s.movieId,
        startsAt: s.startsAt,
        diffusionVersion: s.diffusionVersion,
        projection: s.projection,
        bookingUrl: s.bookingUrl,
      });
    }

    return { deleted: old.length, inserted: screenings.length };
  },
});

/** Suppression définitive d'un cinéma par supabaseId (+ ses séances, cascade
 * manuelle — les films sont conservés, comme l'exige le cutover). */
export const deleteCinemaBySupabaseId = mutation({
  args: { supabaseId: v.string() },
  handler: async (ctx, { supabaseId }) => {
    const doc = await ctx.db
      .query("cinemas")
      .withIndex("by_supabaseId", (q) => q.eq("supabaseId", supabaseId))
      .first();
    if (!doc) return { success: true, deleted: false, screeningsDeleted: 0 };

    const screenings = await ctx.db
      .query("screenings")
      .withIndex("by_cinemaId", (q) => q.eq("cinemaId", supabaseId))
      .collect();
    for (const s of screenings) await ctx.db.delete(s._id);

    await ctx.db.delete(doc._id);
    return { success: true, deleted: true, screeningsDeleted: screenings.length };
  },
});

// ─────────────────────────────────────────────────────────────────────────────
// Queries
// ─────────────────────────────────────────────────────────────────────────────

/** Tous les cinémas (id = supabaseId). Ordre par nom asc. */
export const getCinemas = query({
  args: {},
  handler: async (ctx) => {
    const docs = await ctx.db.query("cinemas").collect();
    return docs
      .sort((a, b) => a.name.localeCompare(b.name))
      .map((c) => ({
        id: c.supabaseId,
        name: c.name,
        slug: c.slug,
        allocineId: c.allocineId,
        address: c.address ?? null,
        website: c.website ?? null,
      }));
  },
});

/**
 * Séances à partir d'une date (défaut : maintenant) avec film et cinéma joints
 * en JS (3 lectures indexées, pas de v.id()). Retourne une liste plate, chaque
 * séance portant son `movie` complet — le client regroupe par `movie.id` pour
 * reconstruire le shape du site (CinemaMovie + screenings).
 *
 * `fromMs`/`toMs` bornent startsAt (par défaut fromMs = maintenant, toMs non
 * borné). `limit` plafonné à 20000 : les séances sont ordonnées par startsAt
 * asc, les jours demandés par les ponts caches sont donc toujours en tête.
 *
 * Scan borné : le balayage passe d'abord par `.take(limit)` (index by_startsAt,
 * gte fromMs), PUIS `toMs` est appliqué en JS. Le filtrer dans la query
 * obligeait Convex à parcourir l'index jusqu'à la fin — c.-à-d. toutes les
 * séances futures — même pour répondre à un jour précis.
 */
export const getScreeningsWithMovieCinema = query({
  args: {
    fromMs: v.optional(v.number()),
    toMs: v.optional(v.number()),
    limit: v.optional(v.number()),
  },
  handler: async (ctx, args) => {
    const from = args.fromMs ?? Date.now();
    const limit = Math.min(Math.max(1, args.limit ?? 5000), 20000);

    let screenings = await ctx.db
      .query("screenings")
      .withIndex("by_startsAt", (qq) => qq.gte("startsAt", from))
      .order("asc")
      .take(limit);

    // Borne haute appliquée après take() : scan plafonné à `limit`, pas à tout
    // l'index. Une journée ≈ 80 séances → bien en vue de la tête de liste.
    if (args.toMs !== undefined) {
      screenings = screenings.filter((s) => s.startsAt <= args.toMs!);
    }

    // Jointures en JS : volumes petits (3 cinémas, ~293 films), collect OK.
    const movies = await ctx.db.query("movies").collect();
    const cinemas = await ctx.db.query("cinemas").collect();
    const movieById = new Map(movies.map((m) => [m.supabaseId, m]));
    const cinemaById = new Map(cinemas.map((c) => [c.supabaseId, c]));

    return screenings.map((s) => {
      const movie = movieById.get(s.movieId);
      const cinema = cinemaById.get(s.cinemaId);
      return {
        id: s.supabaseId,
        cinemaId: s.cinemaId,
        cinemaName: cinema?.name ?? "",
        cinemaSlug: cinema?.slug ?? "",
        startsAt: s.startsAt,
        diffusionVersion: s.diffusionVersion,
        projection: s.projection,
        bookingUrl: s.bookingUrl ?? null,
        movie: movie
          ? {
              id: movie.supabaseId,
              allocineId: movie.allocineId,
              title: movie.title,
              originalTitle: movie.originalTitle ?? null,
              synopsis: movie.synopsis ?? null,
              posterUrl: movie.posterUrl ?? null,
              trailerUrl: movie.trailerUrl ?? null,
              runtime: movie.runtime ?? null,
              genres: movie.genres ?? null,
              director: movie.director ?? null,
              cast: movie.cast ?? null,
              ageRating: movie.ageRating ?? null,
              userRating: movie.userRating ?? null,
              pressRating: movie.pressRating ?? null,
            }
          : null,
      };
    });
  },
});
