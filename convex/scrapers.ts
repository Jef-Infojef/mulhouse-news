import { mutation, query } from "./_generated/server";
import { v } from "convex/values";

// ─────────────────────────────────────────────────────────────────────────────
// Phase 3 — fonctions Convex consommées par les scrapers Python (GitHub Actions)
// via le client HTTP `scripts/convex_client.py` (endpoints /api/query et
// /api/mutation, auth `Authorization: Convex <deploy key>`).
//
// Conventions :
//  • Dédup articles par clé naturelle `link` (upsert en deux temps : lookup
//    by_link puis insert/patch — les champs fournis sont mis à jour, les autres
//    conservés).
//  • `supabaseId` = UUID Supabase d'origine : les nouveaux articles scrapés
//    reçoivent un UUID frais généré côté Python, ce qui permet de joindre
//    articleGoogleTags/articleImages (ces tables stockent cet UUID).
//  • Pas de .collect() sur les grosses tables : scans bornés avec .take() ;
//    `content` n'est JAMAIS renvoyé par les queries de liste (égress).
// ─────────────────────────────────────────────────────────────────────────────

const EBRA_DOMAINS = ["lalsace.fr", "dna.fr", "estrepublicain.fr", "vosgesmatin.fr"];

// ─────────────────────────────────────────────────────────────────────────────
// Mutations
// ─────────────────────────────────────────────────────────────────────────────

export const upsertArticle = mutation({
  args: {
    row: v.object({
      link: v.string(),
      title: v.optional(v.string()),
      imageUrl: v.optional(v.string()),
      imageCaption: v.optional(v.string()),
      source: v.optional(v.string()),
      description: v.optional(v.string()),
      publishedAt: v.optional(v.number()),
      scrapedAt: v.optional(v.number()),
      createdAt: v.optional(v.number()),
      updatedAt: v.optional(v.number()),
      content: v.optional(v.string()),
      localImage: v.optional(v.string()),
      r2Url: v.optional(v.string()),
      hidden: v.optional(v.boolean()),
      supabaseId: v.optional(v.string()),
    }),
  },
  handler: async (ctx, { row }) => {
    const existing = await ctx.db
      .query("articles")
      .withIndex("by_link", (q) => q.eq("link", row.link))
      .first();

    if (existing) {
      const patch: Record<string, unknown> = {};
      const keys = [
        "title",
        "imageUrl",
        "imageCaption",
        "source",
        "description",
        "publishedAt",
        "scrapedAt",
        "content",
        "localImage",
        "r2Url",
        "hidden",
      ] as const;
      for (const key of keys) {
        if (row[key] !== undefined) patch[key] = row[key];
      }
      if (row.supabaseId !== undefined && existing.supabaseId !== row.supabaseId) {
        patch["supabaseId"] = row.supabaseId;
      }
      patch["updatedAt"] = row.updatedAt ?? Date.now();
      await ctx.db.patch(existing._id, patch);
      return { created: false, id: existing._id, supabaseId: existing.supabaseId ?? null };
    }

    const id = await ctx.db.insert("articles", {
      title: row.title ?? "",
      link: row.link,
      imageUrl: row.imageUrl,
      imageCaption: row.imageCaption,
      source: row.source,
      description: row.description,
      publishedAt: row.publishedAt ?? Date.now(),
      scrapedAt: row.scrapedAt ?? Date.now(),
      createdAt: row.createdAt ?? Date.now(),
      updatedAt: row.updatedAt ?? Date.now(),
      content: row.content,
      localImage: row.localImage,
      r2Url: row.r2Url,
      hidden: row.hidden ?? false,
      supabaseId: row.supabaseId,
    });
    return { created: true, id, supabaseId: row.supabaseId ?? null };
  },
});

export const upsertArticleImages = mutation({
  args: {
    rows: v.array(
      v.object({
        articleId: v.string(), // UUID Supabase d'origine (clé de jointure)
        url: v.string(),
        caption: v.optional(v.string()),
        position: v.number(),
        source: v.optional(v.string()),
        localImage: v.optional(v.string()),
        r2Url: v.optional(v.string()),
        createdAt: v.optional(v.number()),
      })
    ),
  },
  handler: async (ctx, { rows }) => {
    let inserted = 0;
    let updated = 0;
    for (const row of rows) {
      const existing = await ctx.db
        .query("articleImages")
        .withIndex("by_articleId", (q) => q.eq("articleId", row.articleId))
        .filter((q) => q.eq(q.field("url"), row.url))
        .first();
      if (existing) {
        const patch: Record<string, unknown> = {};
        if (row.caption !== undefined) patch["caption"] = row.caption;
        if (row.source !== undefined) patch["source"] = row.source;
        if (row.localImage !== undefined) patch["localImage"] = row.localImage;
        if (row.r2Url !== undefined) patch["r2Url"] = row.r2Url;
        patch["position"] = row.position;
        await ctx.db.patch(existing._id, patch);
        updated++;
      } else {
        await ctx.db.insert("articleImages", {
          articleId: row.articleId,
          url: row.url,
          caption: row.caption,
          position: row.position,
          source: row.source,
          localImage: row.localImage,
          r2Url: row.r2Url,
          createdAt: row.createdAt ?? Date.now(),
        });
        inserted++;
      }
    }
    return { inserted, updated };
  },
});

export const upsertArticleGoogleTags = mutation({
  args: {
    rows: v.array(
      v.object({ articleId: v.string(), tagId: v.string() })
    ),
  },
  handler: async (ctx, { rows }) => {
    let inserted = 0;
    for (const row of rows) {
      const existing = await ctx.db
        .query("articleGoogleTags")
        .withIndex("by_articleId", (q) => q.eq("articleId", row.articleId))
        .filter((q) => q.eq(q.field("tagId"), row.tagId))
        .first();
      if (!existing) {
        await ctx.db.insert("articleGoogleTags", {
          articleId: row.articleId,
          tagId: row.tagId,
        });
        inserted++;
      }
    }
    return { inserted };
  },
});

export const insertScrapingLog = mutation({
  args: {
    startedAt: v.number(),
    finishedAt: v.optional(v.number()),
    status: v.string(),
    isConnected: v.boolean(),
    articlesCount: v.number(),
    successCount: v.number(),
    errorCount: v.number(),
    details: v.optional(v.any()),
    errorMessage: v.optional(v.string()),
  },
  handler: async (ctx, args) => {
    await ctx.db.insert("scrapingLogs", {
      startedAt: args.startedAt,
      finishedAt: args.finishedAt,
      status: args.status,
      isConnected: args.isConnected,
      articlesCount: args.articlesCount,
      successCount: args.successCount,
      errorCount: args.errorCount,
      details: args.details,
      errorMessage: args.errorMessage,
    });
    return { success: true };
  },
});

export const deleteArticleByLink = mutation({
  args: { link: v.string() },
  handler: async (ctx, { link }) => {
    const doc = await ctx.db
      .query("articles")
      .withIndex("by_link", (q) => q.eq("link", link))
      .first();
    if (!doc) return { success: true, deleted: false };
    if (doc.supabaseId) {
      const articleSupabaseId = doc.supabaseId;
      const tags = await ctx.db
        .query("articleGoogleTags")
        .withIndex("by_articleId", (q) => q.eq("articleId", articleSupabaseId))
        .take(100);
      for (const tag of tags) await ctx.db.delete(tag._id);
      const images = await ctx.db
        .query("articleImages")
        .withIndex("by_articleId", (q) => q.eq("articleId", articleSupabaseId))
        .take(100);
      for (const image of images) await ctx.db.delete(image._id);
    }
    await ctx.db.delete(doc._id);
    return { success: true, deleted: true };
  },
});

// ─────────────────────────────────────────────────────────────────────────────
// Queries
// ─────────────────────────────────────────────────────────────────────────────

export const getArticleByLink = query({
  args: { link: v.string() },
  handler: async (ctx, { link }) => {
    const doc = await ctx.db
      .query("articles")
      .withIndex("by_link", (q) => q.eq("link", link))
      .first();
    if (!doc) return null;
    // `content` exclu (égress) : les scrapers ne réutilisent que l'existence
    // et les métadonnées.
    return {
      id: doc._id,
      title: doc.title,
      link: doc.link,
      imageUrl: doc.imageUrl ?? null,
      imageCaption: doc.imageCaption ?? null,
      source: doc.source ?? null,
      description: doc.description ?? null,
      publishedAt: doc.publishedAt,
      scrapedAt: doc.scrapedAt ?? null,
      createdAt: doc.createdAt ?? null,
      updatedAt: doc.updatedAt ?? null,
      localImage: doc.localImage ?? null,
      r2Url: doc.r2Url ?? null,
      hidden: doc.hidden,
      supabaseId: doc.supabaseId ?? null,
    };
  },
});

export const getArticleLinks = query({
  args: {
    source: v.optional(v.string()),
    cursor: v.optional(v.union(v.null(), v.string())),
    limit: v.optional(v.number()),
  },
  handler: async (ctx, { source, cursor, limit }) => {
    const numItems = Math.min(Math.max(1, limit ?? 200), 500);
    if (source) {
      const res = await ctx.db
        .query("articles")
        .withIndex("by_source", (q) => q.eq("source", source))
        .paginate({ cursor: cursor ?? null, numItems });
      return {
        links: res.page.map((doc) => doc.link),
        cursor: res.continueCursor,
        isDone: res.isDone,
      };
    }
    const res = await ctx.db.query("articles").paginate({ cursor: cursor ?? null, numItems });
    return {
      links: res.page.map((doc) => doc.link),
      cursor: res.continueCursor,
      isDone: res.isDone,
    };
  },
});

export const getArticlesShortContent = query({
  args: {
    limit: v.optional(v.number()),
    hours: v.optional(v.number()),
    minLength: v.optional(v.number()),
  },
  handler: async (ctx, args) => {
    const limit = Math.min(Math.max(1, args.limit ?? 50), 200);
    const hours = args.hours ?? 24;
    const minLength = args.minLength ?? 500;
    const cutoff = Date.now() - hours * 3600_000;

    // Scan borné des articles récents (hidden=false, publishedAt desc) puis
    // filtre en JS sur content (pas d'index possible sur le contenu).
    const candidates = await ctx.db
      .query("articles")
      .withIndex("by_hidden_publishedAt", (q) => q.eq("hidden", false))
      .order("desc")
      .take(Math.min(Math.max(limit * 2, 40), 80));
    const articles = [];
    for (const doc of candidates) {
      if (doc.publishedAt < cutoff) continue;
      const short = doc.content === undefined || doc.content === null || doc.content.length < minLength;
      if (!short) continue;
      articles.push({
        id: doc._id,
        title: doc.title,
        link: doc.link,
        imageUrl: doc.imageUrl ?? null,
        imageCaption: doc.imageCaption ?? null,
        source: doc.source ?? null,
        description: doc.description ?? null,
        publishedAt: doc.publishedAt,
        supabaseId: doc.supabaseId ?? null,
      });
      if (articles.length >= limit) break;
    }
    return { articles };
  },
});

// Articles EBRA (lalsace.fr) au contenu manquant, SANS borne de date —
// backfill d'archive (scrape_content_full.py --archive). Scan paginé du plus
// ancien au plus récent (publishedAt asc) : les vieux articles sont traités
// en premier, et chaque run avance naturellement (contenu rempli → filtré).
export const getArticlesMissingContentAll = query({
  args: {
    limit: v.optional(v.number()),
    maxPages: v.optional(v.number()),
    pageSize: v.optional(v.number()),
    minLength: v.optional(v.number()),
  },
  handler: async (ctx, args) => {
    const limit = Math.min(Math.max(1, args.limit ?? 300), 500);
    const maxPages = Math.min(Math.max(1, args.maxPages ?? 200), 1000);
    const pageSize = Math.min(Math.max(1, args.pageSize ?? 500), 1000);
    const minLength = args.minLength ?? 150;
    const articles = [];
    let cursor: string | null = null;
    for (let page = 0; page < maxPages; page++) {
      const res = await ctx.db
        .query("articles")
        .withIndex("by_hidden_publishedAt", (q) => q.eq("hidden", false))
        .order("asc")
        .paginate({ cursor, numItems: pageSize });
      for (const doc of res.page) {
        if (!doc.link || !doc.link.includes("lalsace.fr")) continue;
        const short = doc.content === undefined || doc.content === null || doc.content.length < minLength;
        if (!short) continue;
        articles.push({
          id: doc._id,
          title: doc.title,
          link: doc.link,
          imageUrl: doc.imageUrl ?? null,
          imageCaption: doc.imageCaption ?? null,
          source: doc.source ?? null,
          description: doc.description ?? null,
          publishedAt: doc.publishedAt,
          supabaseId: doc.supabaseId ?? null,
        });
        if (articles.length >= limit) return { articles };
      }
      if (res.isDone) break;
      cursor = res.continueCursor;
    }
    return { articles };
  },
});

export const getArticleByTitleRecent = query({
  args: { title: v.string(), hours: v.optional(v.number()) },
  handler: async (ctx, { title, hours }) => {
    const cutoff = Date.now() - (hours ?? 48) * 3600_000;
    // Index by_title : 1–N docs du même titre, pas un scan de 500 articles
    // complets (content inclus) à chaque item RSS — ça vidait le Database I/O
    // Convex (plusieurs Go/jour, déploiement coupé le 2026-08-16).
    const candidates = await ctx.db
      .query("articles")
      .withIndex("by_title", (q) => q.eq("title", title))
      .take(20);
    const doc = candidates.find((d) => d.publishedAt >= cutoff);
    if (!doc) return null;
    return {
      id: doc._id,
      title: doc.title,
      link: doc.link,
      publishedAt: doc.publishedAt,
      supabaseId: doc.supabaseId ?? null,
    };
  },
});

export const getArticleByImage = query({
  args: { imageUrl: v.string(), startMs: v.number(), endMs: v.number() },
  handler: async (ctx, { imageUrl, startMs, endMs }) => {
    const candidates = await ctx.db
      .query("articles")
      .withIndex("by_imageUrl", (q) => q.eq("imageUrl", imageUrl))
      .take(20);
    const doc = candidates.find((d) => d.publishedAt >= startMs && d.publishedAt <= endMs);
    if (!doc) return null;
    return {
      id: doc._id,
      title: doc.title,
      link: doc.link,
      publishedAt: doc.publishedAt,
      supabaseId: doc.supabaseId ?? null,
    };
  },
});

// Rattrapage des légendes photo EBRA (articles récents sans imageCaption mais
// avec imageUrl). Approx. de `WHERE link LIKE '%lalsace.fr%' ... ORDER BY
// publishedAt DESC LIMIT 30` : scan borné des plus récents puis filtre JS.
export const getArticlesMissingCaptions = query({
  args: { limit: v.optional(v.number()) },
  handler: async (ctx, args) => {
    const limit = Math.min(Math.max(1, args.limit ?? 30), 100);
    const candidates = await ctx.db
      .query("articles")
      .withIndex("by_publishedAt")
      .order("desc")
      .take(80);
    const rows = [];
    for (const doc of candidates) {
      const hasImage = doc.imageUrl !== undefined && doc.imageUrl !== null && doc.imageUrl !== "";
      if (doc.imageCaption || !hasImage) continue;
      if (!EBRA_DOMAINS.some((domain) => doc.link.includes(domain))) continue;
      rows.push({ id: doc._id, link: doc.link });
      if (rows.length >= limit) break;
    }
    return { rows };
  },
});

export const getNewsTags = query({
  args: {},
  handler: async (ctx) => {
    const docs = await ctx.db.query("newsTags").collect();
    return docs.map((doc) => ({
      // l'id utilisé pour ArticleGoogleTag est l'UUID Supabase (supabaseId)
      id: doc.supabaseId ?? doc._id,
      name: doc.name,
      slug: doc.slug,
    }));
  },
});

// Articles récents (hidden=false, updatedAt récent, content non vide) pour le
// sync RAG. Approx. de `WHERE hidden=false AND updatedAt > NOW()-25h ORDER BY
// updatedAt DESC LIMIT N` : scan borné par publishedAt desc puis filtre JS.
// `content` est renvoyé ici (le RAG en a besoin) — query dédiée, jamais de liste.
export const getRecentArticlesWithContent = query({
  args: { limit: v.optional(v.number()), hours: v.optional(v.number()) },
  handler: async (ctx, args) => {
    const limit = Math.min(Math.max(1, args.limit ?? 250), 1000);
    const hours = args.hours ?? 25;
    const cutoff = Date.now() - hours * 3600_000;
    const candidates = await ctx.db
      .query("articles")
      .withIndex("by_hidden_publishedAt", (q) => q.eq("hidden", false))
      .order("desc")
      .take(Math.min(Math.max(limit * 2, 40), 120));
    const articles = [];
    for (const doc of candidates) {
      if (typeof doc.updatedAt !== "number" || doc.updatedAt < cutoff) continue;
      if (!doc.content || doc.content.length < 40) continue;
      articles.push({
        // sourceId stable du RAG = UUID Supabase d'origine (sinon _id Convex)
        id: doc.supabaseId ?? doc._id,
        supabaseId: doc.supabaseId ?? null,
        title: doc.title,
        description: doc.description ?? null,
        content: doc.content,
        source: doc.source ?? null,
        link: doc.link,
        publishedAt: doc.publishedAt,
        updatedAt: doc.updatedAt,
      });
      if (articles.length >= limit) break;
    }
    return { articles };
  },
});
