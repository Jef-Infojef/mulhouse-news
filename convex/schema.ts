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
});