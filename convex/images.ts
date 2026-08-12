import { mutation, query } from "./_generated/server";
import { v } from "convex/values";

// ─────────────────────────────────────────────────────────────────────────────
// Phase 4 — fonctions Convex des scripts TS d'images (download_images.ts /
// sync_to_b2.ts), portés Prisma → Convex.
//
// Le script `download_images.ts` télécharge localement les images (public/
// article-images/) puis patche `localImage` ; `sync_to_b2.ts` upload sur B2
// puis patche `r2Url`. Ces mutations remplacent les `prisma.article.update` /
// `prisma.articleImage.update` d'origine.
//
// Rappel du portage Prisma → Convex :
//  • `id` renvoyé par les queries = `_id` Convex (les mutations l'utilisent
//    via `v.id("articles")` / `v.id("articleImages")`).
//  • `supabaseId` = UUID Supabase d'origine (ex-cuid) : sert de nom de fichier
//    pour les articles (stabilité des clés B2) et de clé de jointure pour les
//    articleImages (champ `articleId`).
//  • Les scans sont bornés (index + .take()) ou paginés (cursor) : jamais de
//    .collect() sur les grosses tables.
// ─────────────────────────────────────────────────────────────────────────────

const DEFAULT_HOURS = 48;

// Articles dont l'image principale est à télécharger. Reproduit le findMany
// Prisma d'origine :
//   imageUrl non nul / non vide ('' / 'null'), ET
//   ( localImage null  OU  ( localImage non null ET r2Url null ) ), ET
//   publishedAt >= startMs (par défaut now - 48h).
// Paginée (cursor) — le client boucle jusqu'à isDone.
// NB : `startMs` doit être fourni par le client (calculé une seule fois avant
// la boucle) : un `Date.now()` côté handler changerait la borne entre deux
// pages et invaliderait le cursor de pagination (InvalidCursor).
export const getImagesToDownload = query({
  args: {
    cursor: v.optional(v.union(v.null(), v.string())),
    limit: v.optional(v.number()),
    startMs: v.optional(v.number()),
  },
  handler: async (ctx, { cursor, limit, startMs }) => {
    const numItems = Math.min(Math.max(1, limit ?? 200), 500);
    const cutoff = startMs ?? Date.now() - DEFAULT_HOURS * 3600_000;
    const res = await ctx.db
      .query("articles")
      .withIndex("by_publishedAt", (q) => q.gte("publishedAt", cutoff))
      .order("desc")
      .paginate({ cursor: cursor ?? null, numItems });
    const articles = [];
    for (const doc of res.page) {
      const imageUrl = doc.imageUrl;
      const hasImageUrl =
        imageUrl !== undefined &&
        imageUrl !== null &&
        imageUrl !== "" &&
        imageUrl !== "null";
      if (!hasImageUrl) continue;
      const needsDownload =
        doc.localImage == null || (doc.localImage != null && doc.r2Url == null);
      if (!needsDownload) continue;
      articles.push({
        id: doc._id,
        supabaseId: doc.supabaseId ?? null,
        imageUrl,
        link: doc.link,
        localImage: doc.localImage ?? null,
        r2Url: doc.r2Url ?? null,
      });
    }
    return {
      articles,
      cursor: res.continueCursor,
      isDone: res.isDone,
    };
  },
});

// Images de galerie (articleImages) à télécharger. articleImages ne référence
// l'article QUE par UUID Supabase (champ `articleId`) : on joint en JS —
// d'abord les articles récents (48h) via l'index publishedAt, puis pour chacun
// ses images via l'index by_articleId. Filtre identique : localImage null OU
// (localImage non null ET r2Url null). Bornée (pas de pagination : jointure
// N+1 sur des petites listes).
export const getArticleImagesToDownload = query({
  args: { limit: v.optional(v.number()), hours: v.optional(v.number()) },
  handler: async (ctx, { limit, hours }) => {
    const limit_ = Math.min(Math.max(1, limit ?? 500), 2000);
    const cutoff = Date.now() - (hours ?? DEFAULT_HOURS) * 3600_000;
    const recentArticles = await ctx.db
      .query("articles")
      .withIndex("by_publishedAt", (q) => q.gte("publishedAt", cutoff))
      .order("desc")
      .take(Math.min(limit_, 300));
    const images = [];
    for (const article of recentArticles) {
      if (!article.supabaseId) continue;
      const articleSupabaseId = article.supabaseId;
      const articleImages = await ctx.db
        .query("articleImages")
        .withIndex("by_articleId", (q) => q.eq("articleId", articleSupabaseId))
        .take(50);
      for (const img of articleImages) {
        const needsDownload =
          img.localImage == null || (img.localImage != null && img.r2Url == null);
        if (!needsDownload) continue;
        images.push({
          id: img._id,
          url: img.url,
          localImage: img.localImage ?? null,
          r2Url: img.r2Url ?? null,
          supabaseId: articleSupabaseId,
          articleLink: article.link,
        });
        if (images.length >= limit_) return { images };
      }
    }
    return { images };
  },
});

// Articles à uploader sur B2 : localImage non null ET r2Url null.
// Scan BORNÉ et INDEXÉ (by_publishedAt desc, articles récents) + filtre JS :
// un filtre Convex sur toute la table lirait les `content` HTML volumineux des
// 27k articles → "Too many bytes read" (16 Mo par exécution). Le pipeline réel
// n'upload que des images fraîchement téléchargées (fenêtre 48h, comme
// download_images) : le scan des articles récents couvre l'usage normal.
export const getImagesToUpload = query({
  args: { limit: v.optional(v.number()), hours: v.optional(v.number()) },
  handler: async (ctx, { limit, hours }) => {
    const limit_ = Math.min(Math.max(1, limit ?? 500), 2000);
    const cutoff = Date.now() - (hours ?? DEFAULT_HOURS) * 3600_000;
    const candidates = await ctx.db
      .query("articles")
      .withIndex("by_publishedAt", (q) => q.gte("publishedAt", cutoff))
      .order("desc")
      .take(limit_);
    const articles = [];
    for (const doc of candidates) {
      if (
        typeof doc.localImage === "string" &&
        doc.localImage.length > 0 &&
        doc.r2Url == null
      ) {
        articles.push({
          id: doc._id,
          supabaseId: doc.supabaseId ?? null,
          localImage: doc.localImage,
          r2Url: doc.r2Url ?? null,
        });
      }
    }
    return { articles };
  },
});

// Images de galerie à uploader sur B2 : localImage non null ET r2Url null.
// Même approche que getArticleImagesToDownload : jointure JS par supabaseId
// (articleImages n'a pas de date propre), fenêtre récente (48h) bornée.
export const getArticleImagesToUpload = query({
  args: { limit: v.optional(v.number()), hours: v.optional(v.number()) },
  handler: async (ctx, { limit, hours }) => {
    const limit_ = Math.min(Math.max(1, limit ?? 500), 2000);
    const cutoff = Date.now() - (hours ?? DEFAULT_HOURS) * 3600_000;
    const recentArticles = await ctx.db
      .query("articles")
      .withIndex("by_publishedAt", (q) => q.gte("publishedAt", cutoff))
      .order("desc")
      .take(Math.min(limit_, 300));
    const images = [];
    for (const article of recentArticles) {
      if (!article.supabaseId) continue;
      const articleSupabaseId = article.supabaseId;
      const articleImages = await ctx.db
        .query("articleImages")
        .withIndex("by_articleId", (q) => q.eq("articleId", articleSupabaseId))
        .take(50);
      for (const img of articleImages) {
        if (
          typeof img.localImage === "string" &&
          img.localImage.length > 0 &&
          img.r2Url == null
        ) {
          images.push({
            id: img._id,
            url: img.url,
            localImage: img.localImage,
            r2Url: img.r2Url ?? null,
          });
          if (images.length >= limit_) return { images };
        }
      }
    }
    return { images };
  },
});

// ─────────────────────────────────────────────────────────────────────────────
// Mutations (patch par `_id` Convex, retourné par les queries ci-dessus)
// ─────────────────────────────────────────────────────────────────────────────

export const updateArticleLocalImage = mutation({
  args: { id: v.id("articles"), localImage: v.optional(v.string()) },
  handler: async (ctx, { id, localImage }) => {
    await ctx.db.patch(id, { localImage, updatedAt: Date.now() });
    return { success: true };
  },
});

export const updateArticleImageLocalImage = mutation({
  args: { id: v.id("articleImages"), localImage: v.optional(v.string()) },
  handler: async (ctx, { id, localImage }) => {
    await ctx.db.patch(id, { localImage });
    return { success: true };
  },
});

export const updateArticleR2Url = mutation({
  args: { id: v.id("articles"), r2Url: v.optional(v.string()) },
  handler: async (ctx, { id, r2Url }) => {
    await ctx.db.patch(id, { r2Url, updatedAt: Date.now() });
    return { success: true };
  },
});

export const updateArticleImageR2Url = mutation({
  args: { id: v.id("articleImages"), r2Url: v.optional(v.string()) },
  handler: async (ctx, { id, r2Url }) => {
    await ctx.db.patch(id, { r2Url });
    return { success: true };
  },
});
