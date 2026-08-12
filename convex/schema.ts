import { defineSchema, defineTable } from "convex/server";
import { v } from "convex/values";

// Note sur les champs de relation (articleId, tagId, newsArticleId, newsTagId) :
// ils sont déclarés en v.string() (et non v.id(...)) car ils contiennent les UUID
// Supabase d'origine, incompatibles avec le format des ids Convex. Les index
// relationnels (by_articleId, etc.) fonctionnent sur ces strings.
// Les requêtes de jointure devront être faites en JS (deux queries), pas via
// v.id() — à réviser après bascule complète si l'on repointe les refs vers Convex.
// DateTime de Prisma → v.number() (epoch ms) ; les collections n'ont pas de champ
// id explicite : l'id Convex auto-généré sert d'identifiant local, les UUID
// Supabase restent présents dans les champs relationnels.
// Les champs timestamp (createdAt, updatedAt, scrapedAt) sont déclarés en
// v.optional(v.number()) : les ~100 documents du spike Phase 0 ont été importés
// avant leur ajout et un champ requis ferait échouer la validation Convex de
// TOUTE la table (lectures bloquées). Les imports de cette Phase 1 fournissent
// toujours ces valeurs.
export default defineSchema({
  articles: defineTable({
    title: v.string(),
    link: v.string(),
    imageUrl: v.optional(v.string()),
    imageCaption: v.optional(v.string()),
    source: v.optional(v.string()),
    description: v.optional(v.string()),
    publishedAt: v.number(),
    scrapedAt: v.optional(v.number()),
    createdAt: v.optional(v.number()),
    updatedAt: v.optional(v.number()),
    content: v.optional(v.string()),
    localImage: v.optional(v.string()),
    r2Url: v.optional(v.string()),
    hidden: v.boolean(),
    // UUID Supabase d'origine (cuid Prisma), backfillé en Phase 2 : nécessaire
    // pour joindre articleGoogleTags/articleImages, qui stockent cet UUID.
    supabaseId: v.optional(v.string()),
  })
    .index("by_link", ["link"])
    .index("by_publishedAt", ["publishedAt"])
    .index("by_hidden_publishedAt", ["hidden", "publishedAt"])
    .index("by_source", ["source"])
    .index("by_supabaseId", ["supabaseId"])
    // Recherche FTS remplaçant les `contains` Prisma (title/description/source).
    // `content` reste volontairement exclu (décision existante côté sécurité).
    .searchIndex("search_title", { searchField: "title", filterFields: ["hidden"] })
    .searchIndex("search_description", { searchField: "description", filterFields: ["hidden"] })
    .searchIndex("search_source", { searchField: "source", filterFields: ["hidden"] }),

  articleImages: defineTable({
    articleId: v.string(), // UUID Supabase d'origine (cf. note en tête de fichier)
    url: v.string(),
    caption: v.optional(v.string()),
    position: v.number(),
    localImage: v.optional(v.string()),
    r2Url: v.optional(v.string()),
    source: v.optional(v.string()),
    createdAt: v.optional(v.number()),
  }).index("by_articleId", ["articleId"]),

  scrapingLogs: defineTable({
    startedAt: v.number(),
    finishedAt: v.optional(v.number()),
    status: v.string(),
    isConnected: v.boolean(),
    articlesCount: v.number(),
    successCount: v.number(),
    errorCount: v.number(),
    details: v.optional(v.any()),
    errorMessage: v.optional(v.string()),
  }).index("by_startedAt", ["startedAt"]),

  appConfig: defineTable({
    key: v.string(),
    value: v.string(),
    updatedAt: v.optional(v.number()),
  }).index("by_key", ["key"]),

  weatherHistory: defineTable({
    location: v.string(),
    day: v.number(),
    month: v.number(),
    year: v.number(),
    tempMax: v.number(),
    tempMin: v.number(),
    weatherCode: v.number(),
    createdAt: v.optional(v.number()),
  })
    .index("by_location_day_month_year", ["location", "day", "month", "year"])
    .index("by_location", ["location"]),

  articleGoogleTags: defineTable({
    articleId: v.string(), // UUID Supabase d'origine (cf. note en tête de fichier)
    tagId: v.string(), // UUID Supabase d'origine (cf. note en tête de fichier)
  })
    .index("by_articleId", ["articleId"])
    .index("by_tagId", ["tagId"]),

  newsArticles: defineTable({
    associationId: v.string(),
    authorId: v.string(),
    title: v.string(),
    slug: v.string(),
    content: v.string(),
    excerpt: v.optional(v.string()),
    featuredImage: v.optional(v.string()),
    status: v.string(),
    statusWorkflow: v.string(),
    publishedAt: v.optional(v.number()),
    hidden: v.boolean(),
    createdAt: v.optional(v.number()),
    updatedAt: v.optional(v.number()),
  })
    .index("by_associationId_slug", ["associationId", "slug"])
    .index("by_slug", ["slug"])
    .index("by_publishedAt", ["publishedAt"])
    .index("by_status", ["status"])
    .index("by_status_publishedAt", ["status", "publishedAt"])
    .index("by_statusWorkflow", ["statusWorkflow"])
    .index("by_hidden", ["hidden"])
    .index("by_associationId", ["associationId"]),

  newsArticleTags: defineTable({
    newsArticleId: v.string(), // UUID Supabase d'origine (cf. note en tête de fichier)
    newsTagId: v.string(), // UUID Supabase d'origine (cf. note en tête de fichier)
  })
    .index("by_newsArticleId", ["newsArticleId"])
    .index("by_newsTagId", ["newsTagId"]),

  newsTags: defineTable({
    associationId: v.string(),
    name: v.string(),
    slug: v.string(),
    color: v.optional(v.string()),
    createdAt: v.optional(v.number()),
    updatedAt: v.optional(v.number()),
    // UUID Supabase d'origine, backfillé en Phase 2 (jointure articleGoogleTags).
    supabaseId: v.optional(v.string()),
  })
    .index("by_associationId_slug", ["associationId", "slug"])
    .index("by_slug", ["slug"])
    .index("by_associationId", ["associationId"])
    .index("by_supabaseId", ["supabaseId"]),

  // ─── Sorties (agenda) — port Supabase → Convex (12/08/2026) ─────────────────
  // Mêmes conventions que les collections existantes : les clés de liaison
  // (associationId, outingId, categoryId) et les `supabaseId` restent en
  // v.string() (UUID Supabase d'origine, jamais des v.id() Convex). Les dates
  // Prisma → v.number() (epoch ms) ; les timestamps createdAt/updatedAt en
  // optionnel pour tolérer les imports antérieurs à leur ajout.
  // NB : OutingTag n'a PAS d'id dans Prisma (PK composite (outingId,
  // categoryId)) — `supabaseId` est donc un UUID v5 déterministe calculé sur le
  // couple, identique côté migration (TS) et côté scraper (Python) pour rester
  // stable et rejouable.

  outings: defineTable({
    supabaseId: v.string(), // UUID Supabase d'origine (id de la ligne Outing)
    associationId: v.string(),
    title: v.string(),
    description: v.optional(v.string()),
    imageUrl: v.optional(v.string()),
    date: v.number(), // epoch ms (début de l'événement)
    endDate: v.optional(v.number()),
    location: v.optional(v.string()),
    price: v.optional(v.string()),
    link: v.optional(v.string()),
    hidden: v.boolean(),
    createdAt: v.optional(v.number()),
    updatedAt: v.optional(v.number()),
  })
    .index("by_date", ["date"])
    .index("by_hidden_date", ["hidden", "date"])
    .index("by_supabaseId", ["supabaseId"]),

  outingCategories: defineTable({
    supabaseId: v.string(), // UUID Supabase d'origine (id de la ligne OutingCategory)
    associationId: v.string(),
    name: v.string(),
    slug: v.string(),
    color: v.optional(v.string()),
    createdAt: v.optional(v.number()),
    updatedAt: v.optional(v.number()),
  })
    .index("by_supabaseId", ["supabaseId"])
    .index("by_slug", ["slug"]),

  outingTags: defineTable({
    supabaseId: v.string(), // UUID v5 déterministe (outingId:categoryId), pas d'id Prisma
    outingId: v.string(), // supabaseId de l'Outing (UUID Supabase d'origine)
    categoryId: v.string(), // supabaseId de l'OutingCategory (UUID Supabase d'origine)
  })
    .index("by_outingId", ["outingId"])
    .index("by_categoryId", ["categoryId"]),

  // ─── Cinémas — port Supabase → Convex (12/08/2026) ─────────────────────────
  // Mêmes conventions que le reste du schéma : les refs (cinemaId, movieId) et
  // les `supabaseId` restent en v.string() (id Prisma d'origine, jamais de
  // v.id() Convex). Le `supabaseId` de chaque collection est l'**id Prisma**
  // Supabase : Cinema.id (cuid), Movie.id (`movie-<allocineId>`),
  // Screening.id (`scr-<cinemaId>-<movieId>-...`) — c'est la clé qui rend le
  // miroir scraper cohérent (le scraper écrit Supabase en premier puis
  // réplique en Convex avec ces mêmes ids).
  // Dates Prisma → v.number() (epoch ms). `runtime` reste une string (valeur
  // texte Allociné stockée telle quelle en Supabase, consommée telle quelle par
  // le site assocommercants).

  cinemas: defineTable({
    supabaseId: v.string(), // id Prisma Cinema (cuid)
    name: v.string(),
    slug: v.string(),
    allocineId: v.string(), // allocineId Prisma (String, unique)
    address: v.optional(v.string()),
    website: v.optional(v.string()),
  })
    .index("by_supabaseId", ["supabaseId"])
    .index("by_allocineId", ["allocineId"])
    .index("by_slug", ["slug"]),

  movies: defineTable({
    supabaseId: v.string(), // id Prisma Movie (`movie-<allocineId>`)
    allocineId: v.number(), // allocineId Prisma (Int, unique)
    title: v.string(),
    originalTitle: v.optional(v.string()),
    synopsis: v.optional(v.string()),
    posterUrl: v.optional(v.string()),
    trailerUrl: v.optional(v.string()),
    runtime: v.optional(v.string()), // durée (texte Allociné)
    genres: v.optional(v.string()),
    director: v.optional(v.string()),
    cast: v.optional(v.string()),
    ageRating: v.optional(v.string()),
    userRating: v.optional(v.number()),
    pressRating: v.optional(v.number()),
    updatedAt: v.optional(v.number()),
  })
    .index("by_supabaseId", ["supabaseId"])
    .index("by_allocineId", ["allocineId"]),

  screenings: defineTable({
    supabaseId: v.string(), // id Prisma Screening (`scr-<cinemaId>-<movieId>-...`)
    cinemaId: v.string(), // supabaseId du Cinema (id Prisma Cinema)
    movieId: v.string(), // supabaseId du Movie (id Prisma Movie)
    startsAt: v.number(), // epoch ms
    diffusionVersion: v.string(), // VF | VO | VOST | VFST
    projection: v.string(), // 2D | 3D | IMAX | 4DX
    bookingUrl: v.optional(v.string()),
  })
    .index("by_supabaseId", ["supabaseId"])
    .index("by_cinemaId", ["cinemaId"])
    .index("by_movieId", ["movieId"])
    .index("by_startsAt", ["startsAt"]),
});