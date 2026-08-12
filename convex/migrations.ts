import { mutation } from "./_generated/server";
import { v } from "convex/values";

// Mutations d'import idempotentes : chaque mutation insère par lots et déduplique
// sur la clé naturelle de la table Supabase d'origine (le 2e passage ne réinsère pas).

export const importArticles = mutation({
  args: {
    rows: v.array(
      v.object({
        title: v.string(),
        link: v.string(),
        imageUrl: v.optional(v.string()),
        imageCaption: v.optional(v.string()),
        source: v.optional(v.string()),
        description: v.optional(v.string()),
        publishedAt: v.number(),
        scrapedAt: v.number(),
        createdAt: v.number(),
        updatedAt: v.number(),
        content: v.optional(v.string()),
        localImage: v.optional(v.string()),
        r2Url: v.optional(v.string()),
        hidden: v.boolean(),
        supabaseId: v.optional(v.string()),
      })
    ),
  },
  handler: async (ctx, { rows }) => {
    let inserted = 0;
    for (const row of rows) {
      const existing = await ctx.db
        .query("articles")
        .withIndex("by_link", (q) => q.eq("link", row.link))
        .first();
      if (existing) continue;
      await ctx.db.insert("articles", row);
      inserted++;
    }
    return { inserted, skipped: rows.length - inserted };
  },
});

export const importArticleImages = mutation({
  args: {
    rows: v.array(
      v.object({
        articleId: v.string(),
        url: v.string(),
        caption: v.optional(v.string()),
        position: v.number(),
        localImage: v.optional(v.string()),
        r2Url: v.optional(v.string()),
        source: v.optional(v.string()),
        createdAt: v.number(),
      })
    ),
  },
  handler: async (ctx, { rows }) => {
    let inserted = 0;
    for (const row of rows) {
      // Dédup par (articleId, url) : index by_articleId puis filtre sur l'url en JS.
      const dup = await ctx.db
        .query("articleImages")
        .withIndex("by_articleId", (q) => q.eq("articleId", row.articleId))
        .filter((q) => q.eq(q.field("url"), row.url))
        .first();
      if (dup) continue;
      await ctx.db.insert("articleImages", row);
      inserted++;
    }
    return { inserted, skipped: rows.length - inserted };
  },
});

export const importScrapingLogs = mutation({
  args: {
    rows: v.array(
      v.object({
        startedAt: v.number(),
        finishedAt: v.optional(v.number()),
        status: v.string(),
        isConnected: v.boolean(),
        articlesCount: v.number(),
        successCount: v.number(),
        errorCount: v.number(),
        details: v.optional(v.any()),
        errorMessage: v.optional(v.string()),
      })
    ),
  },
  handler: async (ctx, { rows }) => {
    let inserted = 0;
    for (const row of rows) {
      // Pas de clé naturelle chez ScrapingLog : dédup approximative par
      // (startedAt, status, articlesCount, successCount, errorCount) — suffisant
      // pour rendre la migration rejouable sans doublonner les mêmes runs.
      const dup = await ctx.db
        .query("scrapingLogs")
        .withIndex("by_startedAt", (q) => q.eq("startedAt", row.startedAt))
        .filter((q) =>
          q.and(
            q.eq(q.field("status"), row.status),
            q.eq(q.field("articlesCount"), row.articlesCount),
            q.eq(q.field("successCount"), row.successCount),
            q.eq(q.field("errorCount"), row.errorCount)
          )
        )
        .first();
      if (dup) continue;
      await ctx.db.insert("scrapingLogs", row);
      inserted++;
    }
    return { inserted, skipped: rows.length - inserted };
  },
});

export const importWeatherHistory = mutation({
  args: {
    rows: v.array(
      v.object({
        location: v.string(),
        day: v.number(),
        month: v.number(),
        year: v.number(),
        tempMax: v.number(),
        tempMin: v.number(),
        weatherCode: v.number(),
        createdAt: v.number(),
      })
    ),
  },
  handler: async (ctx, { rows }) => {
    let inserted = 0;
    for (const row of rows) {
      const dup = await ctx.db
        .query("weatherHistory")
        .withIndex("by_location_day_month_year", (q) =>
          q
            .eq("location", row.location)
            .eq("day", row.day)
            .eq("month", row.month)
            .eq("year", row.year)
        )
        .first();
      if (dup) continue;
      await ctx.db.insert("weatherHistory", row);
      inserted++;
    }
    return { inserted, skipped: rows.length - inserted };
  },
});

export const importArticleGoogleTags = mutation({
  args: {
    rows: v.array(
      v.object({
        articleId: v.string(),
        tagId: v.string(),
      })
    ),
  },
  handler: async (ctx, { rows }) => {
    let inserted = 0;
    for (const row of rows) {
      const dup = await ctx.db
        .query("articleGoogleTags")
        .withIndex("by_articleId", (q) => q.eq("articleId", row.articleId))
        .filter((q) => q.eq(q.field("tagId"), row.tagId))
        .first();
      if (dup) continue;
      await ctx.db.insert("articleGoogleTags", row);
      inserted++;
    }
    return { inserted, skipped: rows.length - inserted };
  },
});

export const importNewsArticles = mutation({
  args: {
    rows: v.array(
      v.object({
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
        createdAt: v.number(),
        updatedAt: v.number(),
      })
    ),
  },
  handler: async (ctx, { rows }) => {
    let inserted = 0;
    for (const row of rows) {
      // Dédup par (associationId, slug) : c'est la contrainte unique Prisma
      // (@@unique([associationId, slug])).
      const dup = await ctx.db
        .query("newsArticles")
        .withIndex("by_associationId_slug", (q) =>
          q.eq("associationId", row.associationId).eq("slug", row.slug)
        )
        .first();
      if (dup) continue;
      await ctx.db.insert("newsArticles", row);
      inserted++;
    }
    return { inserted, skipped: rows.length - inserted };
  },
});

export const importNewsTags = mutation({
  args: {
    rows: v.array(
      v.object({
        associationId: v.string(),
        name: v.string(),
        slug: v.string(),
        color: v.optional(v.string()),
        createdAt: v.number(),
        updatedAt: v.number(),
        supabaseId: v.optional(v.string()),
      })
    ),
  },
  handler: async (ctx, { rows }) => {
    let inserted = 0;
    for (const row of rows) {
      // Dédup par (associationId, slug) : contrainte unique Prisma.
      const dup = await ctx.db
        .query("newsTags")
        .withIndex("by_associationId_slug", (q) =>
          q.eq("associationId", row.associationId).eq("slug", row.slug)
        )
        .first();
      if (dup) continue;
      await ctx.db.insert("newsTags", row);
      inserted++;
    }
    return { inserted, skipped: rows.length - inserted };
  },
});

export const importNewsArticleTags = mutation({
  args: {
    rows: v.array(
      v.object({
        newsArticleId: v.string(),
        newsTagId: v.string(),
      })
    ),
  },
  handler: async (ctx, { rows }) => {
    let inserted = 0;
    for (const row of rows) {
      const dup = await ctx.db
        .query("newsArticleTags")
        .withIndex("by_newsArticleId", (q) => q.eq("newsArticleId", row.newsArticleId))
        .filter((q) => q.eq(q.field("newsTagId"), row.newsTagId))
        .first();
      if (dup) continue;
      await ctx.db.insert("newsArticleTags", row);
      inserted++;
    }
    return { inserted, skipped: rows.length - inserted };
  },
});

export const importAppConfig = mutation({
  args: {
    rows: v.array(
      v.object({
        key: v.string(),
        value: v.string(),
        updatedAt: v.number(),
      })
    ),
  },
  handler: async (ctx, { rows }) => {
    let inserted = 0;
    for (const row of rows) {
      const existing = await ctx.db
        .query("appConfig")
        .withIndex("by_key", (q) => q.eq("key", row.key))
        .first();
      if (existing) continue;
      await ctx.db.insert("appConfig", row);
      inserted++;
    }
    return { inserted, skipped: rows.length - inserted };
  },
});