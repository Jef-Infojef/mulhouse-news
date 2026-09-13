import { query } from "./_generated/server";
import { v } from "convex/values";

// Comptage paginé côté client : chaque page est une exécution de query séparée,
// ce qui évite la limite d'opérations système d'une query unique sur les grosses
// tables (articles ~27k docs avec contenu HTML). Le client boucle sur le cursor.
// Articles SANS photo, comptés par source. Passe par l'index `by_imageUrl` en
// ciblant `imageUrl === undefined` : seuls les documents concernés sont lus, au
// lieu de parcourir les ~130 000 articles pour n'en retenir qu'une fraction.
//
// Le résultat est une LISTE {source, count}, pas un objet indexé par source :
// Convex impose des noms de champs ASCII, et « Libération » ou « L'Équipe » en
// clé font échouer la query.
//
// Même pagination que countTablePage : une exécution par page, réponse réduite
// à des compteurs, le client boucle sur le cursor et additionne.
// Sert à mesurer l'avancement du rattrapage de repair_alsace_articles.py.
export const countMissingPhotoPage = query({
  args: { cursor: v.union(v.null(), v.string()), limit: v.optional(v.number()) },
  handler: async (ctx, { cursor, limit }) => {
    const numItems = Math.min(Math.max(1, limit ?? 200), 1000);
    const res = await ctx.db
      .query("articles")
      .withIndex("by_imageUrl", (q) => q.eq("imageUrl", undefined))
      .paginate({ cursor, numItems });
    const counts = new Map<string, number>();
    let withLocalOrR2 = 0;
    for (const doc of res.page) {
      if (doc.localImage || doc.r2Url) withLocalOrR2++;
      const source = doc.source ?? "(sans source)";
      counts.set(source, (counts.get(source) ?? 0) + 1);
    }
    return {
      bySource: [...counts].map(([source, count]) => ({ source, count })),
      pageSize: res.page.length,
      withLocalOrR2,
      isDone: res.isDone,
      continueCursor: res.continueCursor,
    };
  },
});

// Liens des articles sans photo, paginés. Même index sélectif que
// countMissingPhotoPage, mais renvoie les `link` : c'est ce qui permet de
// croiser le manque avec une autre source (l'ancienne base Supabase, qui a
// conservé des imageUrl perdues à la migration) sans scraper quoi que ce soit.
export const countMissingPhotoLinksPage = query({
  args: { cursor: v.union(v.null(), v.string()), limit: v.optional(v.number()) },
  handler: async (ctx, { cursor, limit }) => {
    const numItems = Math.min(Math.max(1, limit ?? 500), 1000);
    const res = await ctx.db
      .query("articles")
      .withIndex("by_imageUrl", (q) => q.eq("imageUrl", undefined))
      .paginate({ cursor, numItems });
    return {
      links: res.page.map((d) => d.link),
      isDone: res.isDone,
      continueCursor: res.continueCursor,
    };
  },
});

export const countWithPhotoPage = query({
  args: { cursor: v.union(v.null(), v.string()), limit: v.optional(v.number()) },
  handler: async (ctx, { cursor, limit }) => {
    const numItems = Math.min(Math.max(1, limit ?? 500), 1000);
    const res = await ctx.db
      .query("articles")
      .withIndex("by_imageUrl", (q) => q.gt("imageUrl", ""))
      .paginate({ cursor, numItems });
    let withLocal = 0;
    let withR2 = 0;
    for (const doc of res.page) {
      if (doc.localImage) withLocal++;
      if (doc.r2Url) withR2++;
    }
    return {
      pageSize: res.page.length,
      withLocal,
      withR2,
      isDone: res.isDone,
      continueCursor: res.continueCursor,
    };
  },
});

export const alsaceStats = query({
  args: {},
  handler: async (ctx) => {
    // Count sample of archive vs recent
    const archiveCount = (await ctx.db
      .query("articles")
      .withIndex("by_source", (q) => q.eq("source", "L'Alsace (archive)"))
      .take(100)).length;
    const recentSample = await ctx.db
      .query("articles")
      .withIndex("by_source", (q) => q.eq("source", "L'Alsace"))
      .order("desc")
      .take(20);
    const recentMissingPhoto = await ctx.db
      .query("articles")
      .withIndex("by_source", (q) => q.eq("source", "L'Alsace"))
      .filter((q) => q.eq(q.field("imageUrl"), undefined))
      .take(50);
    return {
      recentMissingCount: recentMissingPhoto.length,
      recentSample: recentSample.slice(0, 5).map(a => ({
        date: new Date(a.publishedAt).toISOString().split("T")[0],
        scrapedAt: a.scrapedAt ? new Date(a.scrapedAt).toISOString().split("T")[0] : null,
        title: a.title,
        hasImg: !!a.imageUrl
      }))
    };
  },
});

export const countTablePage = query({
  args: {
    table: v.union(
      v.literal("articles"),
      v.literal("articleImages"),
      v.literal("scrapingLogs"),
      v.literal("appConfig"),
      v.literal("weatherHistory"),
      v.literal("articleGoogleTags"),
      v.literal("newsArticles"),
      v.literal("newsArticleTags"),
      v.literal("newsTags")
    ),
    cursor: v.union(v.null(), v.string()),
  },
  handler: async (ctx, { table, cursor }) => {
    const res = await ctx.db.query(table).paginate({ cursor, numItems: 500 });
    return { count: res.page.length, isDone: res.isDone, continueCursor: res.continueCursor };
  },
});